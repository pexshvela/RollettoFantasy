"""
scheduler.py — Background scheduler.

Every 5 min:
  1. Check watchlist for finished matches → process them
  2. Auto-scan today/yesterday for UCL matches (via list-by-date)

When a match finishes:
  - Fetch lineups → know exactly who played
  - Fetch player stats
  - Award points ONLY to players who actually played (in lineup)
  - Broadcast result
"""
import asyncio
import logging
import unicodedata

import sheets
import football_api
from points_calculator import calc_player_points, build_breakdown
from players import ALL_PLAYERS, get_player_by_espn_name

logger = logging.getLogger(__name__)

_processed: set[str] = set()
POLL_INTERVAL = 5 * 60  # 5 minutes


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


async def run_scheduler(bot=None):
    logger.info("Scheduler started.")
    while True:
        try:
            await check_watchlist(bot)
            await auto_scan_ucl(bot)
            await asyncio.sleep(POLL_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Scheduler error: %s", e)
            await asyncio.sleep(60)


async def check_watchlist(bot=None):
    """Process any watched matches that are now finished."""
    watchlist = await sheets.get_watchlist()
    if not watchlist:
        return
    for entry in watchlist:
        mid = entry["match_id"]
        if mid in _processed:
            continue
        try:
            details = await football_api.get_match_details(mid)
            if not details:
                continue
            if details["status"] == "final":
                logger.info("Watched match finished: %s vs %s",
                            details["home_team"], details["away_team"])
                await process_finished_match(mid, details, bot)
                await sheets.mark_watchlist_processed(mid)
                _processed.add(mid)
            else:
                logger.debug("Match %s still %s", mid, details["status"])
        except Exception as e:
            logger.error("Watchlist check error for %s: %s", mid, e)
        await asyncio.sleep(2)


async def auto_scan_ucl(bot=None):
    """Auto-detect watched tournament matches today/yesterday without manual input."""
    try:
        tournament_ids = await sheets.get_tournament_ids()
        matches = await football_api.get_ucl_matches_today_and_yesterday(tournament_ids)
        for m in matches:
            mid = m["id"]
            if mid in _processed or m["status"] != "final":
                continue
            cached = await sheets.get_cached_match(mid)
            if cached and cached.get("points_awarded"):
                _processed.add(mid)
                continue
            logger.info("Auto-detected finished UCL match: %s vs %s",
                        m["home_team"], m["away_team"])
            await process_finished_match(mid, m, bot)
            _processed.add(mid)
    except Exception as e:
        logger.error("auto_scan_ucl error: %s", e)


async def process_finished_match(match_id: str, match_stub: dict, bot=None):
    """Fetch full match data and award points."""
    # Check not already done
    cached = await sheets.get_cached_match(match_id)
    if cached and cached.get("points_awarded"):
        logger.info("Match %s already processed.", match_id)
        return

    # Fetch everything
    full = await football_api.fetch_full_match(match_id)
    if not full:
        logger.error("Could not fetch full match %s", match_id)
        return

    # Save to cache
    await sheets.save_match_cache(full)

    if not full.get("player_stats"):
        logger.warning("No player stats for %s", match_id)
        if bot:
            await _broadcast(bot, full, points_awarded=False)
        return

    await award_points(full, bot)


async def award_points(match: dict, bot=None):
    """
    Award fantasy points to all users.
    Only players who ACTUALLY PLAYED get points (checked via lineups).
    """
    mid          = match.get("id") or match.get("match_id", "")
    home_team    = match["home_team"]
    away_team    = match["away_team"]
    home_score   = match.get("home_score", 0)
    away_score   = match.get("away_score", 0)
    home_team_id = match.get("home_team_id", "")
    away_team_id = match.get("away_team_id", "")

    player_stats_raw = match.get("player_stats") or {}
    lineups          = match.get("lineups") or {}
    played_ids       = lineups.get("played_ids") or set()  # FlashScore player_ids who played

    # Build team side lookup
    team_side: dict[str, str] = {}
    if home_team_id: team_side[home_team_id] = "home"
    if away_team_id: team_side[away_team_id] = "away"

    def _side_for_team(team_name: str) -> str:
        if _team_matches(team_name, home_team): return "home"
        if _team_matches(team_name, away_team): return "away"
        return ""

    # Build group of bot players per team for fallback matching
    home_bots = {pid: p for pid, p in ALL_PLAYERS.items() if _team_matches(p["team"], home_team)}
    away_bots = {pid: p for pid, p in ALL_PLAYERS.items() if _team_matches(p["team"], away_team)}

    # Map FlashScore stats → bot player_id
    # player_stats_raw is keyed by both flashscore_player_id AND lowercase name
    bot_player_stats: dict[str, dict] = {}

    for key, stats in player_stats_raw.items():
        fs_player_id = stats.get("player_id", "")
        api_name     = stats.get("name", "")
        api_team_id  = stats.get("team_id", "")
        side         = team_side.get(api_team_id, "")

        # ── Check if player actually played ──────────────────────────────────
        # Primary check: FlashScore player_id in played_ids from lineups
        # Fallback: in_lineup=True in player-stats response
        actually_played = (
            (fs_player_id and fs_player_id in played_ids) or
            stats.get("in_lineup", False) or
            int(stats.get("minutes_played") or 0) > 0
        )
        if not actually_played:
            logger.debug("Skipping %s — not in lineup", api_name)
            continue

        # ── Match to bot player ───────────────────────────────────────────────
        bot_player = get_player_by_espn_name(api_name)

        # Discard if name matched but wrong team
        if bot_player and side:
            bp_side = _side_for_team(bot_player["team"])
            if bp_side and bp_side != side:
                bot_player = None

        # Fallback: same team + overlapping name parts
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

        # ── Set clean sheet + goals conceded ─────────────────────────────────
        bp_side = _side_for_team(bot_player["team"]) or side
        if bp_side == "home":
            stats["goals_conceded"] = away_score
            stats["clean_sheet"]    = away_score == 0
        elif bp_side == "away":
            stats["goals_conceded"] = home_score
            stats["clean_sheet"]    = home_score == 0

        bot_player_stats[bot_player["id"]] = stats

    logger.info("Matched %d bot players with stats for %s vs %s",
                len(bot_player_stats), home_team, away_team)

    # Award points to every user
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
            ["gk1"]
            + [f"def{i}" for i in range(1, n_def + 1)]
            + [f"mf{i}"  for i in range(1, n_mid + 1)]
            + [f"fw{i}"  for i in range(1, n_fwd + 1)]
        )
        sub_slots  = [f"sub{i}" for i in range(1, 5)]
        all_slots  = starter_slots + sub_slots
        user_total = 0

        for slot in all_slots:
            pid = squad.get(slot)
            if not pid or pid not in bot_player_stats:
                continue

            stats      = bot_player_stats[pid]
            is_captain = pid == captain_id
            breakdown  = build_breakdown(pid, stats, is_captain)
            breakdown["match"] = (f"{home_team} {home_score}-{away_score} {away_team}")
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
    if points_awarded:
        text = (
            f"⚽ <b>Match Result</b>\n\n"
            f"🏟 <b>{match['home_team']}</b> "
            f"{match['home_score']} - {match['away_score']} "
            f"<b>{match['away_team']}</b>\n\n"
            f"🏆 Points updated! Tap <b>📊 Stats</b> to see your score."
        )
    else:
        text = (
            f"⚽ <b>Match Result</b>\n\n"
            f"🏟 <b>{match['home_team']}</b> "
            f"{match['home_score']} - {match['away_score']} "
            f"<b>{match['away_team']}</b>\n\n"
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
    b = _norm(bot_team)
    a = _norm(api_team)
    ALIASES = {
        "atletico": ["atletico de madrid", "atletico madrid", "atl. madrid", "atl madrid"],
        "psg":      ["paris saint-germain", "paris sg", "paris saint germain"],
        "arsenal":  ["arsenal fc"],
        "liverpool":["liverpool fc"],
        "barcelona":["fc barcelona"],
        "real madrid": ["real madrid cf"],
        "bayern":   ["fc bayern munchen", "fc bayern munich", "bayern munich",
                     "fc bayern munchen", "bavern munchen"],
        "sporting": ["sporting cp", "sporting clube de portugal"],
        "atalanta": ["atalanta bc"],
        "leverkusen": ["bayer leverkusen", "bayer 04 leverkusen"],
        "feyenoord": ["feyenoord rotterdam"],
        "lille":    ["losc lille"],
        "ajax":     ["afc ajax"],
    }
    for canonical, alts in ALIASES.items():
        all_names = [_norm(canonical)] + [_norm(x) for x in alts]
        if b in all_names and a in all_names:
            return True
    return b in a or a in b
