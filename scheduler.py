"""
scheduler.py — Background scheduler for automatic match processing.

Flow:
  - Every 5 min: check watchlist for matches that have finished
  - When a match finishes: fetch stats → award points → broadcast → mark done
  - Pending cache matches (points_awarded=False) are also checked hourly
"""
import asyncio
import logging

import sheets
import football_api
from points_calculator import calc_player_points
from players import ALL_PLAYERS, get_player_by_espn_name

logger = logging.getLogger(__name__)

_processing: set[str] = set()  # prevent double-processing

POLL_INTERVAL = 5 * 60   # check watchlist every 5 minutes


async def run_scheduler(bot=None):
    logger.info("Scheduler started — polling every %d min.", POLL_INTERVAL // 60)
    while True:
        try:
            await check_watchlist(bot)
            await asyncio.sleep(POLL_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Scheduler error: %s", e)
            await asyncio.sleep(60)


async def check_watchlist(bot=None):
    """Check all watched matches — process any that have finished."""
    watchlist = await sheets.get_watchlist()
    if not watchlist:
        return

    logger.info("Checking %d watched match(es)...", len(watchlist))

    for entry in watchlist:
        mid = entry["match_id"]
        if mid in _processing:
            continue

        _processing.add(mid)
        try:
            details = await football_api.get_match_details(mid)
            if not details:
                logger.warning("Could not fetch match %s", mid)
                continue

            if details["status"] == "final":
                logger.info("Match finished: %s vs %s", details["home_team"], details["away_team"])
                await process_finished_match(mid, details, bot)
                await sheets.mark_watchlist_processed(mid)
            else:
                logger.info("Match %s still %s — will check again.", mid, details["status"])

        except Exception as e:
            logger.error("Error checking match %s: %s", mid, e)
        finally:
            _processing.discard(mid)

        # Small delay between API calls to respect rate limits
        await asyncio.sleep(2)


async def process_finished_match(match_id: str, details: dict, bot=None):
    """Fetch full stats, award points, broadcast, cache."""
    # Check not already processed
    cached = await sheets.get_cached_match(match_id)
    if cached and cached.get("points_awarded"):
        logger.info("Match %s already processed — skipping.", match_id)
        return

    # Fetch player stats and events
    player_stats_raw = await football_api.get_player_stats(match_id)
    events = await football_api.get_match_incidents(match_id)
    details["events"] = events
    details["player_stats"] = player_stats_raw or {}

    # Save to match_cache
    await sheets.save_match_cache(details)

    if not player_stats_raw:
        logger.warning("No player stats for %s — saved to cache but no points awarded.", match_id)
        # Broadcast result without points
        if bot:
            await _broadcast_result(bot, details, points_awarded=False)
        return

    # Award points to all users
    await award_points(details, player_stats_raw, bot)


async def award_points(match: dict, player_stats_raw: dict, bot=None):
    """Calculate and save points for every user. Updates total_points."""
    mid = match.get("id") or match.get("match_id", "")
    home_team = match["home_team"]
    away_team = match["away_team"]
    home_score = match.get("home_score", 0)
    away_score = match.get("away_score", 0)
    home_team_id = match.get("home_team_id", "")
    away_team_id = match.get("away_team_id", "")

    # Map FlashScore player names → bot player IDs
    player_stats: dict[str, dict] = {}
    for name_lower, stats in player_stats_raw.items():
        bot_player = get_player_by_espn_name(stats.get("name", name_lower))
        if not bot_player:
            last = name_lower.split()[-1] if name_lower else ""
            if last:
                bot_player = get_player_by_espn_name(last)

        if bot_player:
            # Set clean sheet based on team + final score
            pid_team = bot_player["team"]
            if _team_matches(pid_team, home_team) or stats.get("team_id") == home_team_id:
                stats["goals_conceded"] = away_score
                stats["clean_sheet"] = away_score == 0
            elif _team_matches(pid_team, away_team) or stats.get("team_id") == away_team_id:
                stats["goals_conceded"] = home_score
                stats["clean_sheet"] = home_score == 0
            player_stats[bot_player["id"]] = stats

    logger.info("Matched %d/%d players for %s vs %s",
                len(player_stats), len(player_stats_raw), home_team, away_team)

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
            parts = formation.split("-")
            n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])
        except Exception:
            n_def, n_mid, n_fwd = 4, 3, 3

        starter_slots = (
            ["gk1"]
            + [f"def{i}" for i in range(1, n_def + 1)]
            + [f"mf{i}" for i in range(1, n_mid + 1)]
            + [f"fw{i}" for i in range(1, n_fwd + 1)]
        )
        sub_slots = [f"sub{i}" for i in range(1, 5)]
        all_slots = starter_slots + sub_slots

        user_total_pts = 0

        for slot in all_slots:
            pid = squad.get(slot)
            if not pid:
                continue
            stats = player_stats.get(pid)
            if stats is None:
                continue

            p_obj = ALL_PLAYERS.get(pid)
            position = p_obj.get("position", "FW") if p_obj else "FW"
            is_captain = pid == captain_id

            raw_pts = calc_player_points(pid, stats)
            final_pts = raw_pts * 2 if is_captain else raw_pts

            # Build readable breakdown
            goals_pts = stats.get("goals", 0) * (10 if position in ("GK","DEF") else 5)
            assists_pts = stats.get("assists", 0) * 3
            yellow_pts = stats.get("yellow_cards", 0) * -1
            red_pts = stats.get("red_cards", 0) * -3
            pm_pts = stats.get("penalty_miss", 0) * -2
            cs_pts = (4 if stats.get("clean_sheet") and position in ("GK","DEF")
                      and int(stats.get("minutes_played", 90) or 90) >= 60 else 0)

            breakdown = {
                "goals":              stats.get("goals", 0),
                "goals_pts":          goals_pts,
                "assists":            stats.get("assists", 0),
                "assists_pts":        assists_pts,
                "yellow_cards":       stats.get("yellow_cards", 0),
                "yellow_pts":         yellow_pts,
                "red_cards":          stats.get("red_cards", 0),
                "red_pts":            red_pts,
                "penalty_miss":       stats.get("penalty_miss", 0),
                "pm_pts":             pm_pts,
                "clean_sheet":        bool(stats.get("clean_sheet")),
                "cs_pts":             cs_pts,
                "captain_multiplier": 2 if is_captain else 1,
                "base_pts":           raw_pts,
                "total":              final_pts,
                "match": (f"{match['home_team']} {match['home_score']}"
                          f"-{match['away_score']} {match['away_team']}"),
            }

            await sheets.save_player_match_points(uid, pid, mid, final_pts, breakdown)

            if slot in starter_slots:
                user_total_pts += final_pts

        if user_total_pts != 0:
            current = int(float(user_row.get("total_points") or 0))
            await sheets.update_user(uid, total_points=current + user_total_pts)
            updated += 1

    logger.info("Points awarded to %d users for %s.", updated, mid)
    await sheets.mark_match_points_awarded(mid)

    if bot:
        await _broadcast_result(bot, match, points_awarded=True)


async def _broadcast_result(bot, match: dict, points_awarded: bool):
    users = await sheets.get_all_users()
    if points_awarded:
        text = (
            f"⚽ <b>Match Result</b>\n\n"
            f"🏟 <b>{match['home_team']}</b> "
            f"{match['home_score']} - {match['away_score']} "
            f"<b>{match['away_team']}</b>\n\n"
            f"🏆 Your points have been updated!\n"
            f"Tap <b>📊 Stats</b> to see your score."
        )
    else:
        text = (
            f"⚽ <b>Match Result</b>\n\n"
            f"🏟 <b>{match['home_team']}</b> "
            f"{match['home_score']} - {match['away_score']} "
            f"<b>{match['away_team']}</b>\n\n"
            f"<i>Player stats not available yet.</i>"
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
    b, a = bot_team.lower().strip(), api_team.lower().strip()
    ALIASES = {
        "man city":    ["manchester city"],
        "psg":         ["paris saint-germain", "paris sg", "paris saint germain"],
        "inter":       ["inter milan", "internazionale"],
        "arsenal":     ["arsenal fc"],
        "liverpool":   ["liverpool fc"],
        "barcelona":   ["fc barcelona"],
        "real madrid": ["real madrid cf"],
        "bayern":      ["fc bayern münchen", "fc bayern munich", "bayern munich", "bayern münchen"],
    }
    for canonical, alts in ALIASES.items():
        if b in [canonical] + alts and a in [canonical] + alts:
            return True
    return b in a or a in b
