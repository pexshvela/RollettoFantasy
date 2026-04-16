"""
scheduler.py — Background task for FlashScore-based point automation.

Flow every 30 min on match days:
  1. Get recent UCL matches (from cache first, then API)
  2. For each finished match not yet processed:
     a. Fetch match details + player stats from API
     b. Save to match_cache
     c. For every user: calculate points → save to player_match_points → update total_points
     d. Broadcast result to all users
     e. Mark match as points_awarded = True
"""
import asyncio
import logging
from datetime import date, timedelta

import sheets
import football_api
from points_calculator import calc_player_points
from players import ALL_PLAYERS, get_player_by_espn_name

logger = logging.getLogger(__name__)

_processed_this_session: set[str] = set()

MATCH_DAYS = [
    "2026-04-14", "2026-04-15",  # QF second legs (done)
    "2026-04-29", "2026-04-30",  # SF first legs
    "2026-05-06", "2026-05-07",  # SF second legs
    "2026-05-30",                # Final
]

POLL_MATCHDAY = 30 * 60   # 30 min
POLL_NORMAL   = 4 * 60 * 60  # 4 hours


async def run_scheduler(bot=None):
    logger.info("Scheduler started.")
    while True:
        try:
            today = date.today().isoformat()
            is_match_day = today in MATCH_DAYS
            await check_matches(bot)
            interval = POLL_MATCHDAY if is_match_day else POLL_NORMAL
            logger.info("Next check in %d min.", interval // 60)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Scheduler error: %s", e)
            await asyncio.sleep(60)


async def check_matches(bot=None):
    logger.info("Checking UCL matches...")

    # Get recent matches from API
    matches = await football_api.get_ucl_matches(days_back=2)

    if not matches:
        # Fall back to what's in cache
        cached = await sheets.get_recent_matches(days=2)
        matches = [m for m in cached
                   if m.get("status") == "final" and not m.get("points_awarded")]
        if not matches:
            logger.info("No new finished matches.")
            return

    for m in matches:
        mid = m["id"]
        if not mid or m.get("status") != "final":
            continue
        if mid in _processed_this_session:
            continue

        # Check if already processed in DB
        cached = await sheets.get_cached_match(mid)
        if cached and cached.get("points_awarded"):
            _processed_this_session.add(mid)
            continue

        logger.info("Processing: %s vs %s", m["home_team"], m["away_team"])
        await process_match(m, bot)
        _processed_this_session.add(mid)


async def process_match(match: dict, bot=None):
    mid = match["id"]

    # Fetch player stats from API
    player_stats_raw = await football_api.get_player_stats(mid)

    # Also try to enrich match with full details (events)
    full_details = await football_api.get_match_details(mid)
    if full_details:
        match["events"] = full_details.get("events", [])

    match["player_stats"] = player_stats_raw or {}

    # Save to cache
    await sheets.save_match_cache(match)

    if not player_stats_raw:
        logger.warning("No player stats for match %s — skipping point awards", mid)
        return

    # Calculate and save points for every user
    await award_points(match, player_stats_raw, bot)


async def award_points(match: dict, player_stats_raw: dict, bot=None):
    """
    Match our bot players to the API's player name list,
    calculate points, update every user's squad.
    """
    mid = match["id"]
    home_team = match["home_team"]
    away_team = match["away_team"]
    home_score = match.get("home_score", 0)
    away_score = match.get("away_score", 0)

    # Map bot player IDs → stats
    player_stats: dict[str, dict] = {}
    for name_lower, stats in player_stats_raw.items():
        # Try matching by espn_name
        bot_player = get_player_by_espn_name(stats.get("name", name_lower))
        if not bot_player:
            # Try partial last-name match
            last = name_lower.split(".")[-1].strip()
            bot_player = get_player_by_espn_name(last)
        if bot_player:
            # Add clean sheet info
            if _team_matches(bot_player["team"], home_team):
                stats["goals_conceded"] = away_score
                stats["clean_sheet"] = away_score == 0
            elif _team_matches(bot_player["team"], away_team):
                stats["goals_conceded"] = home_score
                stats["clean_sheet"] = home_score == 0
            player_stats[bot_player["id"]] = stats

    logger.info("Matched %d/%d players with stats", len(player_stats), len(player_stats_raw))

    # Get all users and update
    users = await sheets.get_all_users()
    updated_count = 0

    for user_row in users:
        uid = int(user_row["telegram_id"])
        squad = await sheets.get_squad(uid)
        if not squad:
            continue

        captain_id = user_row.get("captain", "")
        user_total_pts = 0

        all_slots = (
            ["gk1"]
            + [f"def{i}" for i in range(1, 6)]
            + [f"mf{i}" for i in range(1, 6)]
            + [f"fw{i}" for i in range(1, 4)]
            + [f"sub{i}" for i in range(1, 5)]
        )

        for slot in all_slots:
            pid = squad.get(slot)
            if not pid:
                continue
            stats = player_stats.get(pid)
            if stats is None:
                continue

            raw_pts = calc_player_points(pid, stats)
            is_captain = pid == captain_id
            final_pts = raw_pts * 2 if is_captain else raw_pts

            # Build breakdown for display
            p_obj = get_player(pid)
            position = p_obj.get("position", "FW") if p_obj else "FW"
            goals_pts = stats.get("goals", 0) * (10 if position in ("GK", "DEF") else 5)
            assists_pts = stats.get("assists", 0) * 3
            yellow_pts = stats.get("yellow_cards", 0) * -1
            red_pts = stats.get("red_cards", 0) * -3
            pm_pts = stats.get("penalty_miss", 0) * -2
            cs_pts = 4 if stats.get("clean_sheet") and position in ("GK", "DEF") and stats.get("minutes_played", 90) >= 60 else 0

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
                "match":              f"{match['home_team']} {match['home_score']}-{match['away_score']} {match['away_team']}",
            }

            await sheets.save_player_match_points(uid, pid, mid, final_pts, breakdown)

            # Only starters count toward total
            if slot not in [f"sub{i}" for i in range(1, 5)]:
                user_total_pts += final_pts

        if user_total_pts != 0:
            current = int(float(user_row.get("total_points") or 0))
            await sheets.update_user(uid, total_points=current + user_total_pts)
            updated_count += 1

    logger.info("Points awarded to %d users for match %s.", updated_count, mid)
    await sheets.mark_match_points_awarded(mid)

    # Broadcast
    if bot:
        await broadcast_result(bot, match, users)


async def broadcast_result(bot, match: dict, users: list):
    text = (
        f"⚽ <b>Match Result</b>\n\n"
        f"🏟 <b>{match['home_team']}</b> "
        f"{match['home_score']} - {match['away_score']} "
        f"<b>{match['away_team']}</b>\n\n"
        f"🏆 Points updated! Check your stats: tap <b>📊 Stats</b> in the menu."
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
    b, a = bot_team.lower(), api_team.lower()
    ALIASES = {
        "man city":    ["manchester city"],
        "psg":         ["paris saint-germain", "paris saint germain", "paris sg"],
        "inter":       ["inter milan", "internazionale", "fc inter"],
        "arsenal":     ["arsenal fc"],
        "liverpool":   ["liverpool fc"],
        "barcelona":   ["fc barcelona"],
        "real madrid": ["real madrid cf"],
        "bayern":      ["fc bayern münchen", "fc bayern munich", "bayern munich", "bayern münchen"],
    }
    for canonical, alts in ALIASES.items():
        all_names = [canonical] + alts
        if b in all_names and a in all_names:
            return True
    return b in a or a in b


def get_player(pid: str):
    from players import ALL_PLAYERS
    return ALL_PLAYERS.get(pid)
