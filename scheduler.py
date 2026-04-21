"""
scheduler.py — Smart scheduler based on kickoff times.

Flow:
  - /fixtures command fetches all matches and saves to match_cache with kickoff_timestamp
  - Scheduler runs every 5 min but only calls API when:
      * A match's kickoff_timestamp + 105 min (avg match duration) has passed
      * AND match is not yet processed (points_awarded = False)
  - This means 0 API calls on non-match days
  - After kickoff+105min: fetch stats → if not finished yet, retry in 20 min
"""
import asyncio
import logging
import time
import unicodedata

import sheets
import football_api
from points_calculator import calc_player_points, build_breakdown
from players import ALL_PLAYERS, get_player_by_espn_name

logger = logging.getLogger(__name__)

AVG_MATCH_DURATION = 100 * 60   # 100 min — first check (90 + ~10 min buffer)
RETRY_INTERVAL     = 15 * 60    # retry every 15 min if not finished yet
MAX_WAIT           = 60 * 60    # give up after 60 min of retries (AET/penalties edge case)
POLL_INTERVAL      = 5 * 60     # scheduler loop every 5 min

_processing: set[str] = set()


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


async def run_scheduler(bot=None):
    logger.info("Scheduler started — checking every %d min.", POLL_INTERVAL // 60)
    while True:
        try:
            await check_due_matches(bot)
            await asyncio.sleep(POLL_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Scheduler error: %s", e)
            await asyncio.sleep(60)


async def check_due_matches(bot=None):
    """
    Check match_cache for matches that should now be finished.
    Only processes matches where kickoff_timestamp is set AND past due.
    Matches with no kickoff_timestamp are skipped (need /fixtures first).
    """
    now = int(time.time())

    unprocessed = await sheets.get_unprocessed_matches()
    if not unprocessed:
        return

    for match in unprocessed:
        mid          = match.get("match_id") or match.get("id", "")
        kickoff_ts   = int(match.get("kickoff_timestamp") or 0)
        last_checked = int(match.get("last_checked") or 0)

        if not mid:
            continue

        # Skip matches with no kickoff time — these are stale cache entries
        # Run /fixtures to refresh them with proper kickoff times
        if not kickoff_ts:
            continue

        # Not due yet
        if now < kickoff_ts + AVG_MATCH_DURATION:
            continue

        # Skip if checked recently
        if last_checked and now - last_checked < RETRY_INTERVAL:
            continue

        if mid in _processing:
            continue

        _processing.add(mid)
        try:
            logger.info("Checking match %s (%s vs %s)",
                        mid, match.get("home_team"), match.get("away_team"))
            await sheets.update_match_last_checked(mid)
            await process_due_match(mid, match, bot)
        except Exception as e:
            logger.error("Error processing match %s: %s", mid, e)
        finally:
            _processing.discard(mid)

        await asyncio.sleep(2)  # small delay between matches


async def process_due_match(match_id: str, cached_match: dict, bot=None):
    """Fetch latest data and process if finished."""
    # Fetch current match status
    details = await football_api.get_match_details(match_id)
    if not details:
        logger.warning("Could not fetch details for %s", match_id)
        return

    if details["status"] != "final":
        logger.info("Match %s still %s — will retry in %d min",
                    match_id, details["status"], RETRY_INTERVAL // 60)
        return

    # Match is finished — fetch full data
    full = await football_api.fetch_full_match(match_id)
    if not full:
        return

    # Update cache with final score and stats
    await sheets.save_match_cache(full)

    if not full.get("player_stats"):
        logger.warning("No player stats for %s", match_id)
        if bot:
            await _broadcast(bot, full, points_awarded=False)
        return

    await award_points(full, bot)


async def award_points(match: dict, bot=None):
    """Calculate and save fantasy points for all users."""
    mid          = match.get("id") or match.get("match_id", "")
    home_team    = match["home_team"]
    away_team    = match["away_team"]
    home_score   = match.get("home_score", 0)
    away_score   = match.get("away_score", 0)
    home_team_id = match.get("home_team_id", "")
    away_team_id = match.get("away_team_id", "")

    player_stats_raw = match.get("player_stats") or {}
    lineups          = match.get("lineups") or {}
    played_ids       = lineups.get("played_ids") or set()

    team_side = {}
    if home_team_id: team_side[home_team_id] = "home"
    if away_team_id: team_side[away_team_id] = "away"

    def _side_for_team(team_name: str) -> str:
        if _team_matches(team_name, home_team): return "home"
        if _team_matches(team_name, away_team): return "away"
        return ""

    home_bots = {pid: p for pid, p in ALL_PLAYERS.items()
                 if _team_matches(p["team"], home_team)}
    away_bots = {pid: p for pid, p in ALL_PLAYERS.items()
                 if _team_matches(p["team"], away_team)}

    bot_player_stats: dict[str, dict] = {}

    for key, stats in player_stats_raw.items():
        fs_pid      = stats.get("player_id", "")
        api_name    = stats.get("name", "")
        api_team_id = stats.get("team_id", "")
        side        = team_side.get(api_team_id, "")
        minutes     = int(stats.get("minutes_played") or 0)

        # Only players who actually played
        actually_played = (
            (fs_pid and fs_pid in played_ids) or
            stats.get("in_lineup", False) or
            minutes > 0
        )
        if not actually_played:
            continue

        # Match to bot player
        bot_player = get_player_by_espn_name(api_name)
        if bot_player and side:
            bp_side = _side_for_team(bot_player["team"])
            if bp_side and bp_side != side:
                bot_player = None

        if not bot_player and side:
            candidates = home_bots if side == "home" else away_bots
            api_parts = {_norm(p.strip(".")) for p in api_name.replace(".", " ").split()
                         if len(p.strip(".")) > 2}
            for pid, bp in candidates.items():
                if pid in bot_player_stats:
                    continue
                bp_parts = {_norm(p) for p in bp["name"].split() if len(p) > 2}
                if api_parts & bp_parts:
                    bot_player = bp
                    break

        if not bot_player:
            continue

        bp_side = _side_for_team(bot_player["team"]) or side
        if bp_side == "home":
            stats["goals_conceded"] = away_score
            stats["clean_sheet"]    = away_score == 0
        elif bp_side == "away":
            stats["goals_conceded"] = home_score
            stats["clean_sheet"]    = home_score == 0

        bot_player_stats[bot_player["id"]] = stats

    logger.info("Matched %d bot players for %s vs %s",
                len(bot_player_stats), home_team, away_team)

    users = await sheets.get_all_users()
    updated = 0

    for user_row in users:
        uid = int(user_row["telegram_id"])
        squad = await sheets.get_squad(uid)
        if not squad:
            continue

        captain_id = user_row.get("captain", "")
        try:
            formation = squad.get("formation", "4-3-3") or "4-3-3"
            p = formation.split("-")
            n_def, n_mid, n_fwd = int(p[0]), int(p[1]), int(p[2])
        except Exception:
            n_def, n_mid, n_fwd = 4, 3, 3

        starter_slots = (
            ["gk1"] +
            [f"def{i}" for i in range(1, n_def + 1)] +
            [f"mf{i}"  for i in range(1, n_mid + 1)] +
            [f"fw{i}"  for i in range(1, n_fwd + 1)]
        )
        sub_slots = [f"sub{i}" for i in range(1, 5)]
        user_total = 0

        for slot in starter_slots + sub_slots:
            pid = squad.get(slot)
            if not pid or pid not in bot_player_stats:
                continue
            stats      = bot_player_stats[pid]
            is_captain = pid == captain_id
            breakdown  = build_breakdown(pid, stats, is_captain)
            breakdown["match"] = f"{home_team} {home_score}-{away_score} {away_team}"
            final_pts  = breakdown.get("total", 0)
            await sheets.save_player_match_points(uid, pid, mid, final_pts, breakdown)
            if slot in starter_slots:
                user_total += final_pts

        if user_total != 0:
            current = int(float(user_row.get("total_points") or 0))
            await sheets.update_user(uid, total_points=current + user_total)
            updated += 1

    logger.info("Points awarded to %d users for match %s.", updated, mid)
    await sheets.mark_match_points_awarded(mid)
    if bot:
        await _broadcast(bot, match, points_awarded=True)


async def _broadcast(bot, match: dict, points_awarded: bool):
    users = await sheets.get_all_users()
    score = f"{match['home_score']}-{match['away_score']}"
    if points_awarded:
        text = (
            f"⚽ <b>Match Result</b>\n\n"
            f"🏟 <b>{match['home_team']}</b> {score} <b>{match['away_team']}</b>\n\n"
            f"🏆 Points updated! Tap <b>📊 Stats</b> to see your score."
        )
    else:
        text = (
            f"⚽ <b>Match Result</b>\n\n"
            f"🏟 <b>{match['home_team']}</b> {score} <b>{match['away_team']}</b>\n\n"
            f"<i>Player stats updating...</i>"
        )
    sent = 0
    for u in users:
        try:
            await bot.send_message(int(u["telegram_id"]), text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    logger.info("Broadcast sent to %d users.", sent)


def _team_matches(bot_team: str, api_team: str) -> bool:
    if not bot_team or not api_team:
        return False
    b, a = _norm(bot_team), _norm(api_team)
    ALIASES = {
        "atletico":  ["atletico de madrid", "atletico madrid"],
        "psg":       ["paris saint-germain", "paris sg"],
        "arsenal":   ["arsenal fc"],
        "liverpool": ["liverpool fc"],
        "barcelona": ["fc barcelona"],
        "real madrid": ["real madrid cf"],
        "bayern":    ["fc bayern munchen", "fc bayern munich", "bayern munich"],
        "sporting":  ["sporting cp"],
        "atalanta":  ["atalanta bc"],
        "leverkusen":["bayer leverkusen", "bayer 04 leverkusen"],
    }
    for canonical, alts in ALIASES.items():
        all_names = [_norm(canonical)] + [_norm(x) for x in alts]
        if b in all_names and a in all_names:
            return True
    return b in a or a in b
