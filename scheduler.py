"""
scheduler.py — Background task that runs every 30 min on match days,
detects finished UCL matches, calculates fantasy points, and updates
all users in Supabase.

Flow:
  1. Call /scores to get UCL matches
  2. Find matches with status == "final" not yet processed
  3. For each final match, for each bot player on those teams:
     - Call /athlete/eventlog?playerId={espn_id}
     - Get stats for that match date
  4. For each user, sum up points and update total_points
  5. Optionally broadcast leaderboard update
"""
import asyncio
import logging
from datetime import datetime, timezone, date

import sheets
import football_api
from points_calculator import total_squad_points
from players import ALL_PLAYERS

logger = logging.getLogger(__name__)

# ── In-memory set of already-processed match IDs (resets on restart) ─────────
_processed: set[str] = set()

# Match days — scheduler polls more frequently on these dates (UTC)
# Update this list each matchday
MATCH_DAYS: list[str] = [
    "2026-04-15",  # QF second legs
    "2026-04-14",
    # Add SF and Final dates here:
    # "2026-04-28", "2026-04-29",  # SF first legs
    # "2026-05-05", "2026-05-06",  # SF second legs
    # "2026-05-30",                # Final
]

# How often to check (seconds)
POLL_INTERVAL_MATCHDAY   = 30 * 60   # 30 min on match days
POLL_INTERVAL_NORMAL     = 4 * 60 * 60  # 4 hours otherwise


async def run_scheduler(bot=None):
    """Main scheduler loop — call this as a background asyncio task."""
    logger.info("Scheduler started.")
    while True:
        try:
            today = date.today().isoformat()
            is_match_day = today in MATCH_DAYS
            await check_and_process_matches(bot)
            interval = POLL_INTERVAL_MATCHDAY if is_match_day else POLL_INTERVAL_NORMAL
            logger.info("Next check in %d minutes.", interval // 60)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Scheduler cancelled.")
            break
        except Exception as e:
            logger.error("Scheduler error: %s", e)
            await asyncio.sleep(60)  # wait 1 min and retry on error


async def check_and_process_matches(bot=None):
    """Fetch scores, find newly finished matches, process them."""
    logger.info("Checking UCL scores...")
    matches = await football_api.get_scores()

    for match in matches:
        match_id = match["id"]
        if match["status"] != "final":
            continue
        if match_id in _processed:
            continue

        logger.info("Processing finished match: %s vs %s (%s)",
                    match["homeTeam"], match["awayTeam"], match.get("date", ""))

        try:
            await process_match(match, bot)
            _processed.add(match_id)
        except Exception as e:
            logger.error("Failed to process match %s: %s", match_id, e)


async def process_match(match: dict, bot=None):
    """
    For a finished match:
    1. Find which bot players played for the two teams
    2. Fetch their stats via /athlete/eventlog
    3. Update all users' total_points
    """
    home_team = match["homeTeam"]
    away_team = match["awayTeam"]
    match_date = str(match.get("date", ""))[:10]  # YYYY-MM-DD

    # Find bot players who played in this match
    relevant_players = [
        p for p in ALL_PLAYERS.values()
        if _team_matches(p["team"], home_team) or _team_matches(p["team"], away_team)
    ]

    if not relevant_players:
        logger.warning("No bot players found for %s vs %s", home_team, away_team)
        return

    logger.info("Fetching stats for %d players...", len(relevant_players))

    # Fetch stats for each player (with small delay to respect rate limits)
    player_stats: dict[str, dict] = {}
    for p in relevant_players:
        espn_id = p.get("espn_id")
        if not espn_id:
            logger.warning("No ESPN ID for %s — skipping", p["name"])
            continue
        stats = await football_api.get_player_match_stats(espn_id, match_date)
        if stats:
            player_stats[p["id"]] = stats
            logger.info("%s: goals=%s ast=%s yc=%s rc=%s",
                        p["name"], stats.get("goals"), stats.get("assists"),
                        stats.get("yellow_cards"), stats.get("red_cards"))
        else:
            # Player didn't play or no data — 0 points
            player_stats[p["id"]] = {"goals": 0, "assists": 0, "yellow_cards": 0,
                                      "red_cards": 0, "penalty_miss": 0, "minutes_played": 0}
        await asyncio.sleep(1.5)  # ~1.5s between calls → safe within rate limit

    if not player_stats:
        logger.warning("No stats collected for this match.")
        return

    # Determine clean sheets
    home_clean = match["awayScore"] == 0
    away_clean = match["homeScore"] == 0
    for p in relevant_players:
        pid = p["id"]
        if pid not in player_stats:
            continue
        if _team_matches(p["team"], home_team):
            player_stats[pid]["goals_conceded"] = match["awayScore"]
            player_stats[pid]["clean_sheet"] = home_clean
        else:
            player_stats[pid]["goals_conceded"] = match["homeScore"]
            player_stats[pid]["clean_sheet"] = away_clean

    # Now update every user's total_points
    await award_points_to_all_users(player_stats)

    # Broadcast leaderboard if bot is provided
    if bot:
        await broadcast_match_result(bot, match, player_stats)


async def award_points_to_all_users(player_stats: dict[str, dict]):
    """Add match points to every registered user's total."""
    users = await sheets.get_all_users()
    updated = 0
    for user in users:
        uid = int(user["telegram_id"])
        squad = await sheets.get_squad(uid)
        if not squad:
            continue

        pts = total_squad_points(squad, player_stats)
        if pts == 0:
            continue

        current = int(float(user.get("total_points") or 0))
        await sheets.update_user(uid, total_points=current + pts)
        updated += 1

    logger.info("Awarded points to %d users.", updated)


async def broadcast_match_result(bot, match: dict, player_stats: dict):
    """Send match result + top scorers to all users."""
    try:
        users = await sheets.get_all_users()
        result_text = (
            f"⚽ <b>Match Result</b>\n\n"
            f"🏟 <b>{match['homeTeam']}</b> {match['homeScore']} - "
            f"{match['awayScore']} <b>{match['awayTeam']}</b>\n\n"
            f"🏆 Leaderboard updated! Check your points from the home screen."
        )
        sent = 0
        for user in users:
            try:
                await bot.send_message(
                    int(user["telegram_id"]),
                    result_text,
                    parse_mode="HTML"
                )
                sent += 1
                await asyncio.sleep(0.05)  # avoid flood limits
            except Exception:
                pass
        logger.info("Broadcast sent to %d users.", sent)
    except Exception as e:
        logger.error("Broadcast error: %s", e)


def _team_matches(bot_team: str, api_team: str) -> bool:
    """Fuzzy match bot team name to API team name."""
    if not bot_team or not api_team:
        return False
    b = bot_team.lower().strip()
    a = api_team.lower().strip()

    # Direct match
    if b == a:
        return True

    # Common aliases
    ALIASES = {
        "man city":  ["manchester city"],
        "psg":       ["paris saint-germain", "paris sg", "paris saint germain"],
        "inter":     ["inter milan", "fc inter", "internazionale"],
        "arsenal":   ["arsenal fc"],
        "liverpool": ["liverpool fc"],
        "barcelona": ["fc barcelona"],
        "real madrid": ["real madrid cf"],
        "bayern":    ["fc bayern münchen", "fc bayern munich", "bayern munich", "bayern münchen"],
    }

    for canonical, alternatives in ALIASES.items():
        if b == canonical or b in alternatives:
            if a == canonical or a in alternatives:
                return True

    # Partial: one contains the other
    return b in a or a in b
