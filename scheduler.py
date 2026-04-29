"""
scheduler.py — Background tasks:
1. Check matches due for processing (kickoff + 100 min)
2. Award points to confirmed squads only
3. Send notifications (deadlines, results)
4. Auto-detect gameweeks from fixtures
"""
import asyncio
import logging
import time
import unicodedata
from datetime import datetime, timezone, timedelta

import sheets
import football_api
from players import get_all_players, find_player_by_name, get_player, set_active_tournament as _set_tournament
from points_calculator import calc_points, build_breakdown
import config

logger = logging.getLogger(__name__)

# Ensure player lookup uses correct tournament
def _ensure_tournament():
    try:
        _set_tournament(config.DEFAULT_TOURNAMENT.lower())
    except Exception:
        pass

POLL_INTERVAL    = config.SCHEDULER_POLL_MINUTES * 60
MATCH_DUE_MIN    = config.MATCH_DUE_MINUTES * 60
RETRY_MIN        = config.MATCH_RETRY_MINUTES * 60

_processing: set[str] = set()


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


async def run_scheduler(bot=None):
    logger.info("Scheduler started.")
    while True:
        try:
            await check_due_matches(bot)
            await check_deadline_notifications(bot)
            await check_transfer_window_notifications(bot)
            await check_admin_reminders(bot)
        except Exception as e:
            logger.error("Scheduler error: %s", e)
        await asyncio.sleep(POLL_INTERVAL)


# ── Match processing ──────────────────────────────────────────────────────────

async def check_due_matches(bot=None):
    now     = int(time.time())
    matches = await sheets.get_unprocessed_matches()
    if not matches:
        return

    for m in matches:
        mid          = m.get("match_id", "")
        kickoff_ts   = int(m.get("kickoff_timestamp") or 0)
        last_checked = int(m.get("last_checked") or 0)

        if not mid or not kickoff_ts:
            continue

        # Not due yet
        if now < kickoff_ts + MATCH_DUE_MIN:
            continue

        # Skip if checked recently
        if last_checked and now - last_checked < RETRY_MIN:
            continue

        if mid in _processing:
            continue

        _processing.add(mid)
        try:
            await process_match(mid, m, bot)
        except Exception as e:
            logger.error("Error processing match %s: %s", mid, e)
        finally:
            _processing.discard(mid)

        await asyncio.sleep(2)


async def process_match(match_id: str, cached: dict, bot=None):
    """Fetch match result and award points if finished."""
    await sheets.update_match_last_checked(match_id)

    _ensure_tournament()
    details = await football_api.get_match_details(match_id)
    if not details:
        logger.warning("Could not fetch match %s", match_id)
        return

    if details["status"] != "final":
        logger.info("Match %s still %s — retry in %d min",
                    match_id, details["status"], config.MATCH_RETRY_MINUTES)
        return

    logger.info("Match finished: %s vs %s", details["home_team"], details["away_team"])

    # Fetch full data
    full = await football_api.fetch_full_match(match_id)
    if not full:
        return

    await sheets.save_match_cache(full)

    if not full.get("player_stats"):
        logger.warning("No player stats for %s — broadcasting result only", match_id)
        if bot:
            await broadcast_result(bot, full)
        return

    await award_points(full, bot)


async def award_points(match: dict, bot=None):
    """Award points to all users with confirmed squads."""
    mid        = match.get("id") or match.get("match_id", "")
    home_team  = match["home_team"]
    away_team  = match["away_team"]
    home_score = match.get("home_score", 0)
    away_score = match.get("away_score", 0)
    home_tid   = match.get("home_team_id", "")
    away_tid   = match.get("away_team_id", "")

    player_stats_raw = match.get("player_stats") or {}
    played_ids       = set(match.get("played_ids") or set())

    # Also add players from lineups home/away starters and subs to played_ids
    # This handles cases where player_stats has 0 minutes but player actually played
    lineups = match.get("lineups") or {}
    for side in ("home", "away"):
        for entry in lineups.get(f"{side}_starters", []):
            pid = str(entry.get("player_id", "")) if isinstance(entry, dict) else str(entry)
            if pid:
                played_ids.add(pid)
        for entry in lineups.get(f"{side}_subs", []):
            pid = str(entry.get("player_id", "")) if isinstance(entry, dict) else str(entry)
            # Only add subs if they have actual minutes in player_stats (came on)
            if pid and any(str(ps.get("player_id","")) == pid and int(ps.get("minutes_played") or 0) > 0
                           for ps in player_stats_raw):
                played_ids.add(pid)

    # Build team side map
    team_side = {}
    if home_tid: team_side[home_tid] = "home"
    if away_tid: team_side[away_tid] = "away"

    def _side_for_team(team_name: str) -> str:
        n = _norm(team_name)
        hn = _norm(home_team)
        an = _norm(away_team)
        if n == hn or n in hn or hn in n: return "home"
        if n == an or n in an or an in n: return "away"
        return ""

    # Map API players → our player IDs
    bot_player_stats: dict[str, dict] = {}
    all_bot_players = get_all_players()

    for key, stats in player_stats_raw.items():
        api_name    = stats.get("name", "")
        api_team_id = stats.get("team_id", "")
        minutes     = int(stats.get("minutes_played") or 0)
        api_pid     = stats.get("player_id", "")

        # Only players who played
        # Also check lineup names for players with 0 minutes
        # Only score players who actually played (minutes > 0 from API)
        # Lineup-based fallbacks are removed as they cause false positives
        # (e.g. subs who were listed but never came on)
        actually_played = minutes > 0
        if not actually_played:
            continue

        side = team_side.get(api_team_id, "")

        # Find matching bot player by name
        bot_player = find_player_by_name(api_name)

        # Verify team side
        if bot_player and side:
            bp_side = _side_for_team(bot_player["team"])
            if bp_side and bp_side != side:
                bot_player = None

        if not bot_player:
            continue

        # Set clean sheet and goals conceded
        bp_side = _side_for_team(bot_player["team"]) or side
        if bp_side == "home":
            stats["goals_conceded"] = away_score
            stats["clean_sheet"]    = away_score == 0
        elif bp_side == "away":
            stats["goals_conceded"] = home_score
            stats["clean_sheet"]    = home_score == 0

        # If player has NO stats entry at all (not tracked by API) but is confirmed
        # as a starter via lineup data, give them 1 minute so appearance pts are awarded.
        # ONLY do this if the API has no minutes data at all (not if API explicitly says 0)
        # stats.get("minutes_played") is None means no data; 0 means API says didn't play
        # No minutes override needed - trust API data directly
        bot_player_stats[bot_player["id"]] = stats

    logger.info("Matched %d/%d players for %s vs %s",
                len(bot_player_stats), len(player_stats_raw), home_team, away_team)

    # Log unmatched players for debugging
    for key, stats in player_stats_raw.items():
        api_name = stats.get("name", "")
        pid_norm = _norm(api_name)
        matched  = any(p["name"] == find_player_by_name(api_name)["name"]
                       for p in [find_player_by_name(api_name)] if p)                    if find_player_by_name(api_name) else False
        if not find_player_by_name(api_name):
            logger.warning("NO MATCH for API player: '%s'", api_name)
        else:
            logger.debug("Matched '%s' -> '%s'", api_name, find_player_by_name(api_name)["name"])

    # Find gameweek by match date
    match_date = match.get("date", "") or match.get("match_date", "")
    all_gws    = await sheets.get_all_gameweeks()
    gw_id      = 0

    # 1. Exact date match (start_date <= match_date <= end_date)
    for gw in all_gws:
        start = gw.get("start_date", "")
        end   = gw.get("end_date", "") or start
        if start and start <= match_date <= end:
            gw_id = gw["id"]
            break

    # 2. Fallback: gameweek whose start_date matches
    if not gw_id:
        for gw in all_gws:
            if gw.get("start_date") == match_date:
                gw_id = gw["id"]
                break

    # 3. Fallback: closest upcoming gameweek by start_date
    if not gw_id:
        upcoming = [g for g in all_gws if g.get("start_date", "") <= match_date]
        if upcoming:
            gw_id = sorted(upcoming, key=lambda g: g.get("start_date",""), reverse=True)[0]["id"]

    # 4. Last resort: first gameweek
    if not gw_id and all_gws:
        gw_id = all_gws[0]["id"]

    if not gw_id:
        logger.warning("No gameweek found for match on %s — cannot award points", match_date)
        return

    # Award points to all confirmed squads
    users   = await sheets.get_all_users()
    updated = 0

    for user_row in users:
        uid = int(user_row["telegram_id"])

        confirmation = await sheets.get_confirmation(uid, gw_id)
        if not confirmation:
            continue  # Not confirmed → 0 points

        squad_snapshot = confirmation.get("squad_snapshot") or {}

        # Validate that snapshot IDs are current hash-based IDs
        # Old IDs look like "gk_b43454" (index-based), new ones like "gk_a1b2c3d4" (MD5 hash)
        # Check by trying to look up a player - if none found, use current DB squad
        if squad_snapshot:
            from players import get_player as _gp
            valid_ids = [v for v in squad_snapshot.values()
                        if isinstance(v, str) and v and _gp(v)]
            if not valid_ids:
                logger.warning("User %s: snapshot has unrecognized player IDs — using DB squad", uid)
                squad_snapshot = {}

        if not squad_snapshot:
            # Fallback: use current squad from DB
            db_squad = await sheets.get_squad(uid)
            squad_snapshot = db_squad or {}

            # Validate DB squad too
            if squad_snapshot:
                from players import get_player as _gp2
                valid_db = [v for v in squad_snapshot.values()
                           if isinstance(v, str) and v and _gp2(v)]
                if valid_db:
                    logger.info("User %s: using DB squad with %d valid players", uid, len(valid_db))
                else:
                    logger.warning("User %s: DB squad also has invalid IDs!", uid)

        captain_id = user_row.get("captain", "")
        formation  = user_row.get("formation", "4-3-3")

        logger.info("User %s: formation=%s captain=%s snap_keys=%s",
                    uid, formation, captain_id, list(squad_snapshot.keys())[:5])

        prev_total = 0  # Will be populated if needed

        # Get starter slots using formation-aware helper
        from helpers import get_starter_slots
        starter_slots = get_starter_slots(formation)
        logger.info("User %s: starter_slots=%s", uid, starter_slots)
        user_total    = 0

        for slot in starter_slots:
            pid = squad_snapshot.get(slot)
            if not pid:
                logger.debug("Slot %s is empty", slot)
                continue
            if pid not in bot_player_stats:
                from players import get_player as _gp
                p = _gp(pid)
                logger.warning("Slot %s player '%s' (id=%s) not in bot_player_stats",
                                slot, p["name"] if p else "?", pid)
                continue
            logger.info("Scoring slot %s: %s", slot, pid)

            stats      = bot_player_stats[pid]
            is_captain = pid == captain_id
            breakdown  = build_breakdown(pid, stats, is_captain)
            breakdown["match"] = f"{home_team} {home_score}-{away_score} {away_team}"
            final_pts  = breakdown.get("total", 0)

            await sheets.save_player_points(uid, pid, mid, gw_id, final_pts, breakdown)
            user_total += final_pts

        # Compute total from ALL player_match_points for this user (source of truth)
        all_pts_rows = sheets._get_sb().table("player_match_points").select(
            "points").eq("telegram_id", uid).execute()
        absolute_total = sum(int(r.get("points", 0)) for r in (all_pts_rows.data or []))
        await sheets.update_user(uid, total_points=absolute_total)
        updated += 1

    logger.info("Points awarded to %d users for match %s.", updated, mid)
    await sheets.mark_match_points_awarded(mid)

    if bot:
        await broadcast_result(bot, match)


async def broadcast_result(bot, match: dict):
    users = await sheets.get_all_users()
    text  = (
        f"⚽ <b>Match Result</b>\n\n"
        f"🏟 <b>{match['home_team']}</b> "
        f"{match['home_score']} - {match['away_score']} "
        f"<b>{match['away_team']}</b>\n\n"
        f"🏆 Points updated! Tap 📊 <b>Stats</b> to see your score.\n"
        f"🏆 Check the 🏆 <b>Leaderboard</b> for rankings."
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


# ── Notifications ─────────────────────────────────────────────────────────────

_notified_deadlines: set[str] = set()
_notified_windows:   set[str] = set()


async def check_deadline_notifications(bot=None):
    if not bot:
        return
    deadline = await sheets.get_confirmation_deadline()
    if not deadline:
        return

    try:
        dl = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
    except Exception:
        return

    now     = datetime.now(timezone.utc)
    diff    = (dl - now).total_seconds()
    lang_default = "en"

    users = await sheets.get_all_users()

    # 24h reminder
    key_24h = f"24h:{deadline}"
    if 0 < diff <= 86400 and key_24h not in _notified_deadlines:
        from translations import t
        for u in users:
            lang = u.get("language", "en")
            try:
                await bot.send_message(
                    int(u["telegram_id"]),
                    t(lang, "notif_deadline_24h", deadline=deadline[:16]),
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.05)
            except Exception:
                pass
        _notified_deadlines.add(key_24h)

    # 1h reminder
    key_1h = f"1h:{deadline}"
    if 0 < diff <= 3600 and key_1h not in _notified_deadlines:
        from translations import t
        for u in users:
            lang = u.get("language", "en")
            try:
                await bot.send_message(
                    int(u["telegram_id"]),
                    t(lang, "notif_deadline_1h", deadline=deadline[:16]),
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.05)
            except Exception:
                pass
        _notified_deadlines.add(key_1h)


async def check_transfer_window_notifications(bot=None):
    if not bot:
        return
    from translations import t
    ts  = await sheets.get_transfer_settings()
    now = datetime.now(timezone.utc).isoformat()

    # Window just opened
    key_open = f"open:{ts.get('open','')}"
    if ts.get("open") and ts["open"] <= now and key_open not in _notified_windows:
        users = await sheets.get_all_users()
        for u in users:
            lang = u.get("language", "en")
            try:
                await bot.send_message(
                    int(u["telegram_id"]),
                    t(lang, "notif_window_open", close=(ts.get("close") or "")[:16]),
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.05)
            except Exception:
                pass
        _notified_windows.add(key_open)

    # Window just closed
    key_close = f"close:{ts.get('close','')}"
    if ts.get("close") and ts["close"] <= now and key_close not in _notified_windows:
        users = await sheets.get_all_users()
        for u in users:
            lang = u.get("language", "en")
            try:
                await bot.send_message(
                    int(u["telegram_id"]),
                    t(lang, "notif_window_close"),
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.05)
            except Exception:
                pass
        _notified_windows.add(key_close)


# ── Auto gameweek creation ────────────────────────────────────────────────────

async def check_admin_reminders(bot=None):
    """Send daily reminders to admin at 09:00 UTC when action is needed."""
    if not bot:
        return
    from datetime import datetime, date, timedelta
    import config as _cfg

    now   = datetime.utcnow()
    today = date.today()
    if now.hour != 9:
        return

    key = "admin_reminder_" + today.isoformat()
    if getattr(check_admin_reminders, "_sent", None) == key:
        return
    check_admin_reminders._sent = key

    admin = _cfg.ADMIN_ID
    msgs  = []

    try:
        all_gws  = await sheets.get_all_gameweeks()
        deadline = await sheets.get_confirmation_deadline()
        tw_open  = await sheets.get_setting("transfer_window_open")

        tomorrow  = (today + timedelta(days=1)).isoformat()
        in_2_days = (today + timedelta(days=2)).isoformat()

        has_today    = any(g.get("start_date") == today.isoformat() for g in all_gws)
        has_tomorrow = any(g.get("start_date") == tomorrow for g in all_gws)
        has_2_days   = any(g.get("start_date") == in_2_days for g in all_gws)

        nl = "\n"
        if has_today and not deadline:
            msgs.append(
                "⚠️ <b>Admin Reminder</b>" + nl + nl +
                "Matches TODAY but no deadline set!" + nl + nl +
                "<code>/setdeadline " + today.isoformat() + " 18:00</code>"
            )

        if has_tomorrow and not deadline:
            msgs.append(
                "⚠️ <b>Admin Reminder</b>" + nl + nl +
                "Matches tomorrow <b>" + tomorrow + "</b> — no deadline set!" + nl + nl +
                "<code>/setdeadline " + tomorrow + " 18:00</code>" + nl +
                "<code>/settransfers open " + today.isoformat() + " 10:00 close " + tomorrow + " 17:00 free 1</code>"
            )

        if has_2_days and not tw_open:
            msgs.append(
                "ℹ️ <b>Admin Reminder</b>" + nl + nl +
                "Matches in 2 days <b>" + in_2_days + "</b>" + nl +
                "Consider opening transfers:" + nl + nl +
                "<code>/settransfers open " + today.isoformat() + " 12:00 close " + in_2_days + " 17:00 free 1</code>"
            )

    except Exception as e:
        logger.error("admin reminder error: %s", e)

    for msg in msgs:
        try:
            await bot.send_message(admin, msg, parse_mode="HTML")
        except Exception as e:
            logger.error("admin reminder send: %s", e)



async def auto_create_gameweeks(matches: list):
    """Group matches by date and create gameweeks automatically."""
    from collections import defaultdict
    by_date = defaultdict(list)
    for m in matches:
        by_date[m["date"]].append(m)

    existing_gws = await sheets.get_all_gameweeks()
    existing_dates = {gw.get("start_date") for gw in existing_gws}

    gw_num = len(existing_gws) + 1
    tournament = await sheets.get_tournament()

    for date_str in sorted(by_date.keys()):
        if date_str in existing_dates:
            continue

        # Set deadline 1 hour before first kickoff
        day_matches = sorted(by_date[date_str], key=lambda x: x.get("kickoff_timestamp", 0))
        first_kickoff = day_matches[0].get("kickoff_timestamp", 0)
        if first_kickoff:
            dl = datetime.fromtimestamp(first_kickoff, tz=timezone.utc) - timedelta(hours=1)
            deadline = dl.isoformat()
        else:
            deadline = f"{date_str}T18:00:00+00:00"

        await sheets.create_gameweek(
            name         = f"Gameweek {gw_num}",
            tournament_id= 0,
            start_date   = date_str,
            end_date     = date_str,
            deadline     = deadline,
        )
        logger.info("Created Gameweek %d for %s", gw_num, date_str)
        gw_num += 1
