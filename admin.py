"""
admin.py — Admin commands and panel.
Only accessible by ADMIN_ID.
"""
import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import sheets
import football_api
import players as pl_module
from states import Admin
from translations import t
from inline import admin_keyboard, home_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()


def is_admin(uid: int) -> bool:
    return uid == config.ADMIN_ID


COMMANDS_TEXT = """📖 <b>ADMIN COMMANDS</b>

━━━━━━━━━━━━━━━━━
🏆 <b>TOURNAMENT</b>
━━━━━━━━━━━━━━━━━

/settournament ucl
<i>Switch to UCL player list and fixtures</i>

/settournament pl
<i>Switch to Premier League player list and fixtures</i>

━━━━━━━━━━━━━━━━━
📅 <b>FIXTURES & GAMEWEEKS</b>
━━━━━━━━━━━━━━━━━

/fixtures
<i>Fetch all fixtures from API, save to Supabase, auto-create gameweeks.
Run this at start of campaign or before each matchday.</i>

/rounds
<i>List all gameweeks with dates, deadlines and status.</i>

/setgwstatus ID active|upcoming|finished
<i>Manually update a gameweek status.</i>

━━━━━━━━━━━━━━━━━
⏰ <b>DEADLINES</b>
━━━━━━━━━━━━━━━━━

/setdeadline 35 2026-05-08 18:00
<i>Set squad confirmation deadline for Round 35.
Users must confirm before this time or score 0 for that round.</i>

/setdeadline 2026-05-08 18:00
<i>Set a global deadline (fallback if no round deadline set).</i>

/cleardeadline 35
<i>Remove deadline for Round 35.</i>

/cleardeadline
<i>Remove the global deadline.</i>

━━━━━━━━━━━━━━━━━
🔄 <b>TRANSFERS</b>
━━━━━━━━━━━━━━━━━

/settransfers open 2026-04-27 10:00 close 2026-04-28 20:00 free 2
<i>Set transfer window. free=0 means unlimited.
Format: open YYYY-MM-DD HH:MM close YYYY-MM-DD HH:MM free N</i>

/closetransfers
<i>Immediately close the transfer window.</i>

━━━━━━━━━━━━━━━━━
👥 <b>USERS</b>
━━━━━━━━━━━━━━━━━

/users
<i>List all registered users with points.</i>

/resetuser TELEGRAM_ID
<i>Reset a specific user (squad, points, transfers, confirmation).</i>

/resetall confirm
<i>⚠️ Full campaign reset — wipes ALL users, squads, points, matches.</i>

/wipecache confirm
<i>Delete all match_cache entries. Run before /fixtures for fresh start.</i>

━━━━━━━━━━━━━━━━━
📨 <b>MESSAGING</b>
━━━━━━━━━━━━━━━━━

/broadcast MESSAGE
<i>Send a message to all registered users.</i>

/senduser TELEGRAM_ID MESSAGE
<i>Send a message to a specific user.</i>

━━━━━━━━━━━━━━━━━
🔬 <b>API TESTING</b>
━━━━━━━━━━━━━━━━━

/testapi
<i>Test API connection. Shows upcoming fixtures.</i>

/testmatch FIXTURE_ID
<i>Test fetching a specific match. Shows score, players, events.</i>

/recalculate GAMEWEEK_ID
<i>Re-run points calculation for a gameweek.
Use if stats were wrong the first time.</i>

/recalculate_all
<i>Re-run points calculation for ALL gameweeks with finished matches.
Use after a major fix. Takes longer than a single gameweek recalculation.</i>

/recheck MATCH_ID
<i>Force re-fetch a match result from the API.
Use if a match is stuck as "upcoming" or "scheduled" after it ended.
Example: /recheck 1540842</i>
"""


@router.message(Command("recheck"))
async def cmd_recheck(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: /recheck MATCH_ID\nExample: /recheck 1540842")
        return
    match_id = parts[1].strip()
    # Reset match cache so scheduler picks it up again
    try:
        sheets._get_sb().table("match_cache").update({
            "status": "upcoming",
            "last_checked": 0,
            "points_awarded": False
        }).eq("match_id", match_id).execute()
        await message.answer(
            f"✅ Match <code>{match_id}</code> queued for recheck.\n"
            f"The scheduler will fetch the result within 5 minutes.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")


# ── Admin panel ───────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "⚙️ <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


@router.callback_query(F.data == "admin:commands")
async def show_commands(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Back to Admin", callback_data="admin:back")
    kb.button(text="🏠 Home",          callback_data="home:back")
    kb.adjust(1)
    await callback.message.edit_text(
        COMMANDS_TEXT, parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "⚙️ <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )
    await callback.answer()


# ── Tournament ────────────────────────────────────────────────────────────────

@router.message(Command("settournament"))
async def cmd_settournament(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2 or parts[1] not in ("ucl", "pl"):
        await message.answer("Usage: /settournament ucl | pl")
        return
    t_name = parts[1]
    await sheets.set_setting("active_tournament", t_name)
    pl_module.set_active_tournament(t_name)
    await message.answer(f"✅ Tournament set to <b>{t_name.upper()}</b>", parse_mode="HTML")


# ── Fixtures & Gameweeks ──────────────────────────────────────────────────────

@router.message(Command("fixtures"))
async def cmd_fixtures(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await message.answer("🔄 Fetching fixtures from API...")

    tournament = await sheets.get_tournament()
    pl_module.set_active_tournament(tournament)

    # Clear existing gameweeks and match cache before repopulating
    await message.answer("🗑 Clearing old gameweeks and match cache...")
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None,
            lambda: sheets._get_sb().table("gameweeks").delete().gte("id", 0).execute())
    except Exception:
        pass
    try:
        await loop.run_in_executor(None,
            lambda: sheets._get_sb().table("match_cache").delete().neq("match_id", "x").execute())
    except Exception:
        pass

    matches = await football_api.get_all_fixtures(tournament)
    if not matches:
        await message.answer("❌ No fixtures found. Check API key and tournament setting.")
        return

    from datetime import date
    today    = date.today().isoformat()
    week_ago = (date.today() - __import__("datetime").timedelta(days=7)).isoformat()
    relevant = [m for m in matches if m["date"] >= week_ago]

    # Save to cache
    saved = 0
    for m in relevant:
        existing = await sheets.get_cached_match(m["id"])
        if not existing:
            if m["status"] == "final" and m["date"] < today:
                m["points_awarded"] = True  # old results — skip processing
            await sheets.save_match_cache(m)
            saved += 1

    # Auto-create gameweeks
    from scheduler import auto_create_gameweeks
    await auto_create_gameweeks([m for m in relevant if m["date"] >= today])

    past   = [m for m in relevant if m["date"] < today and m["status"] == "final"]
    future = [m for m in relevant if m["date"] >= today]

    lines = [
        f"✅ <b>Fixtures loaded — {len(relevant)} matches</b>",
        f"Saved {saved} new to cache.",
        "",
    ]

    if past:
        lines.append("<b>Recent results:</b>")
        for m in past[-5:]:
            lines.append(f"  {m['date']}: {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']}")

    if future:
        lines.append("")
        lines.append(f"<b>Upcoming ({len(future)} matches):</b>")
        for m in future[:10]:
            lines.append(f"  📅 {m['date']} {m.get('time','')} — {m['home_team']} vs {m['away_team']} | <code>{m['id']}</code>")

    lines.append("")
    lines.append("Gameweeks auto-created. Use /gameweeks to view.")

    text = "\n".join(lines)
    if len(text) > 4000:
        for i in range(0, len(lines), 30):
            chunk = "\n".join(lines[i:i+30])
            if chunk.strip():
                await message.answer(chunk, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")


@router.message(Command("syncmatches"))
async def cmd_syncmatches(message: Message, state: FSMContext):
    """Add any missing matches from current + next round to match_cache without wiping."""
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔄 Syncing missing matches from API...")

    import football_api as _fapi
    tournament = await sheets.get_tournament()

    current_str = await _fapi.get_current_round(tournament)
    current_num = _fapi.parse_round_number(current_str) if current_str else None
    if not current_num:
        await message.answer("❌ Could not detect current round.")
        return

    added = 0
    skipped = 0
    for round_num in [current_num, current_num + 1]:
        fixtures = await _fapi.get_round_fixtures(tournament, round_num)
        for m in fixtures:
            mid = str(m.get("id") or m.get("match_id", ""))
            if not mid:
                continue
            existing = await sheets.get_cached_match(mid)
            if existing:
                skipped += 1
                continue
            await sheets.save_match_cache(m)
            added += 1

    await message.answer(
        f"✅ Sync complete.\n"
        f"Added: {added} new matches\n"
        f"Already in cache: {skipped}"
    )


@router.message(Command("rounds"))
async def cmd_rounds(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    import football_api as _fapi
    tournament = await sheets.get_tournament()
    current_round_str = await _fapi.get_current_round(tournament)
    current_num = _fapi.parse_round_number(current_round_str) if current_round_str else None
    all_rounds = await _fapi.get_rounds(tournament)

    if not all_rounds:
        await message.answer("❌ Could not fetch rounds from API.")
        return

    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [f"📋 <b>Rounds ({tournament.upper()}):</b>\n"]
    # Only show rounds within ±3 of current to keep message short
    nums = [_fapi.parse_round_number(r) for r in all_rounds if _fapi.parse_round_number(r)]
    if current_num:
        show_nums = [n for n in nums if current_num - 3 <= n <= current_num + 3]
    else:
        show_nums = nums[-7:]  # last 7

    for num in show_nums:
        is_current = num == current_num
        emoji = "🟢" if is_current else ("✅" if current_num and num < current_num else "⏳")
        deadline = await sheets.get_round_deadline(num)
        deadline_str = f" | ⏰ {deadline[:16]}" if deadline else ""
        current_tag = " ← current" if is_current else ""
        lines.append(f"{emoji} <b>Round {num}</b>{deadline_str}{current_tag}")

    lines.append("<i>Use /setdeadline ROUND YYYY-MM-DD HH:MM to set a round deadline</i>")
    lines.append("<i>Use /matchdays ROUND to see fixtures in a round</i>")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("matchdays"))
async def cmd_matchdays(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Usage: /matchdays 35")
        return
    round_num = int(parts[1])
    import football_api as _fapi
    tournament = await sheets.get_tournament()
    fixtures = await _fapi.get_round_fixtures(tournament, round_num)
    if not fixtures:
        await message.answer(f"❌ No fixtures found for Round {round_num}.")
        return

    FINAL = {"final", "ft", "match finished", "aet", "pen", "finished"}
    lines = [f"📋 <b>Round {round_num} fixtures:</b>\n"]
    # Group by date
    by_date: dict[str, list] = {}
    for f in fixtures:
        d = (f.get("date") or f.get("match_date") or "")[:10]
        by_date.setdefault(d, []).append(f)

    for date in sorted(by_date):
        lines.append(f"📅 <b>{date}</b>")
        for f in by_date[date]:
            home = f.get("home_team", "?")
            away = f.get("away_team", "?")
            hs = f.get("home_score")
            aws = f.get("away_score")
            status = str(f.get("status", "")).lower()
            if hs is not None and aws is not None and status in FINAL:
                score = f"{hs}–{aws}"
                emoji = "✅"
            elif status in {"1h", "2h", "ht", "live", "in play"}:
                score = f"{hs}–{aws} 🔴"
                emoji = "🔴"
            else:
                time = (f.get("date") or f.get("match_date") or "")
                score = time[11:16] if len(time) > 15 else "TBD"
                emoji = "⏳"
            lines.append(f"  {emoji} {home} vs {away}  <b>{score}</b>")
        lines.append("")

    deadline = await sheets.get_round_deadline(round_num)
    if deadline:
        lines.append(f"⏰ Deadline: <b>{deadline[:16]}</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("setgwstatus"))
async def cmd_setgwstatus(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer("Usage: /setgwstatus ID active|upcoming|finished")
        return
    gw_id  = int(parts[1])
    status = parts[2]
    if status not in ("active", "upcoming", "finished"):
        await message.answer("Status must be: active, upcoming, or finished")
        return
    await sheets.update_gameweek(gw_id, status=status)
    await message.answer(f"✅ Gameweek {gw_id} status → <b>{status}</b>", parse_mode="HTML")


# ── Deadlines ─────────────────────────────────────────────────────────────────

@router.message(Command("setdeadline"))
async def cmd_setdeadline(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    # Usage A: /setdeadline 35 2026-05-08 18:00  (per round)
    # Usage B: /setdeadline 2026-05-08 18:00     (global fallback)
    try:
        if len(parts) >= 4 and parts[1].isdigit():
            # Per-round deadline
            round_num = int(parts[1])
            dt_str = f"{parts[2]}T{parts[3]}:00+00:00"
            datetime.fromisoformat(dt_str)
            await sheets.set_round_deadline(round_num, dt_str)
            await message.answer(
                f"✅ Deadline for <b>Round {round_num}</b> set:\n<b>{parts[2]} {parts[3]} UTC</b>",
                parse_mode="HTML"
            )
        elif len(parts) >= 3:
            # Global deadline (legacy fallback)
            dt_str = f"{parts[1]}T{parts[2]}:00+00:00"
            datetime.fromisoformat(dt_str)
            await sheets.set_setting("confirmation_deadline", dt_str)
            await message.answer(
                f"✅ Global deadline set:\n<b>{parts[1]} {parts[2]} UTC</b>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "Usage:\n"
                "  /setdeadline 35 2026-05-08 18:00  — set deadline for Round 35\n"
                "  /setdeadline 2026-05-08 18:00      — set global deadline"
            )
    except Exception as e:
        await message.answer(f"❌ Invalid format: {e}")


@router.message(Command("cleardeadline"))
async def cmd_cleardeadline(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) >= 2 and parts[1].isdigit():
        round_num = int(parts[1])
        await sheets.set_round_deadline(round_num, None)
        await message.answer(f"✅ Deadline for Round {round_num} cleared.")
    else:
        await sheets.set_setting("confirmation_deadline", None)
        await message.answer("✅ Global deadline cleared. Squads can confirm anytime.")


# ── Transfers ─────────────────────────────────────────────────────────────────

@router.message(Command("settransfers"))
async def cmd_settransfers(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip()

    try:
        # Parse: /settransfers open YYYY-MM-DD HH:MM close YYYY-MM-DD HH:MM free N
        import re
        open_match  = re.search(r'open\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', text)
        close_match = re.search(r'close\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', text)
        free_match  = re.search(r'free\s+(\d+)', text)

        if not open_match or not close_match:
            raise ValueError("Missing open or close time")

        open_str  = f"{open_match.group(1)}T{open_match.group(2)}:00+00:00"
        close_str = f"{close_match.group(1)}T{close_match.group(2)}:00+00:00"
        free_n    = int(free_match.group(1)) if free_match else config.FREE_TRANSFERS_DEFAULT

        await sheets.set_setting("transfer_window_open",  open_str)
        await sheets.set_setting("transfer_window_close", close_str)
        await sheets.set_setting("free_transfers",        free_n)

        free_label = "∞ (unlimited)" if free_n == 0 else str(free_n)
        await message.answer(
            f"✅ <b>Transfer window set:</b>\n\n"
            f"🔓 Open:  <b>{open_match.group(1)} {open_match.group(2)} UTC</b>\n"
            f"🔒 Close: <b>{close_match.group(1)} {close_match.group(2)} UTC</b>\n"
            f"🎟 Free transfers: <b>{free_label}</b>\n"
            f"💸 Extra transfer cost: -{config.EXTRA_TRANSFER_COST} pts",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            f"❌ Error: {e}\n\n"
            "Usage:\n/settransfers open 2026-04-27 10:00 close 2026-04-28 20:00 free 2\n\n"
            "free=0 means unlimited free transfers"
        )


@router.message(Command("closetransfers"))
async def cmd_closetransfers(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    now = datetime.now(timezone.utc).isoformat()
    await sheets.set_setting("transfer_window_close", now)
    await message.answer("✅ Transfer window closed immediately.")


# ── Users ─────────────────────────────────────────────────────────────────────

@router.message(Command("users"))
async def cmd_users(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    users = await sheets.get_all_users()
    if not users:
        await message.answer("No registered users yet.")
        return

    lines = [f"👥 <b>Users ({len(users)}):</b>\n"]
    for u in sorted(users, key=lambda x: -(x.get("total_points") or 0)):
        conf   = "✅" if u.get("confirmed") else "⏳"
        pts    = u.get("total_points", 0)
        lines.append(
            f"{conf} <code>{u['telegram_id']}</code> — "
            f"<b>{u.get('username','?')}</b> — {pts} pts"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        for i in range(0, len(lines), 30):
            chunk = "\n".join(lines[i:i+30])
            if chunk.strip():
                await message.answer(chunk, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")


@router.message(Command("resetuser"))
async def cmd_resetuser(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: /resetuser TELEGRAM_ID")
        return
    try:
        uid = int(parts[1])
        await sheets.reset_user(uid)
        await message.answer(f"✅ User <code>{uid}</code> reset.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")


@router.message(Command("resetall"))
async def cmd_resetall(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2 or parts[1] != "confirm":
        await message.answer(
            "⚠️ This will delete EVERYTHING.\n\n"
            "To confirm: /resetall confirm"
        )
        return
    await sheets.reset_all()
    await message.answer("✅ Full campaign reset complete.")


@router.message(Command("wipecache"))
async def cmd_wipecache(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2 or parts[1] != "confirm":
        await message.answer(
            "⚠️ This deletes all match_cache entries.\n"
            "Run /fixtures again after.\n\n"
            "To confirm: /wipecache confirm"
        )
        return
    try:
        sheets._get_sb().table("match_cache").delete().neq("match_id", "").execute()
        await message.answer("✅ match_cache wiped. Now run /fixtures.")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")


# ── Messaging ─────────────────────────────────────────────────────────────────

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip()
    if len(text.split("\n", 1)) < 2 and " " not in text[10:]:
        await message.answer("Usage: /broadcast YOUR MESSAGE HERE")
        return

    msg = text.split(" ", 1)[1] if " " in text else ""
    if not msg:
        await message.answer("Usage: /broadcast YOUR MESSAGE HERE")
        return

    users = await sheets.get_all_users()
    sent = 0
    for u in users:
        try:
            await message.bot.send_message(int(u["telegram_id"]), msg, parse_mode="HTML")
            sent += 1
            import asyncio
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ Sent to {sent}/{len(users)} users.")


@router.message(Command("senduser"))
async def cmd_senduser(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split(" ", 2)
    if len(parts) < 3:
        await message.answer("Usage: /senduser TELEGRAM_ID MESSAGE")
        return
    try:
        uid = int(parts[1])
        msg = parts[2]
        await message.bot.send_message(uid, msg, parse_mode="HTML")
        await message.answer(f"✅ Message sent to <code>{uid}</code>.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")


# ── API Testing ───────────────────────────────────────────────────────────────

@router.message(Command("testapi"))
async def cmd_testapi(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    tournament = await sheets.get_tournament()
    await message.answer(f"🔄 Testing API (tournament: {tournament.upper()})...")

    from datetime import date
    matches = await football_api.get_all_fixtures(tournament)

    if not matches:
        await message.answer("❌ No fixtures returned. Check API key.")
        return

    today   = date.today().isoformat()
    future  = [m for m in matches if m["date"] >= today]
    past    = [m for m in matches if m["date"] < today and m["status"] == "final"]

    lines = [
        f"✅ <b>API working!</b>\n",
        f"Total fixtures: {len(matches)}",
        f"Past (finished): {len(past)}",
        f"Upcoming: {len(future)}",
        "",
    ]

    if future[:5]:
        lines.append("<b>Next matches:</b>")
        for m in future[:5]:
            lines.append(
                f"  📅 {m['date']} {m.get('time','')} — "
                f"{m['home_team']} vs {m['away_team']} | <code>{m['id']}</code>"
            )

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("testmatch"))
async def cmd_testmatch(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: /testmatch FIXTURE_ID")
        return
    fid = parts[1]
    await message.answer(f"🔄 Fetching match {fid}...")
    full = await football_api.fetch_full_match(fid)
    if not full:
        await message.answer("❌ Could not fetch match.")
        return

    ps     = full.get("player_stats") or {}
    events = full.get("events") or []
    played = full.get("played_ids") or set()

    lines = [
        f"✅ <b>{full['home_team']} {full['home_score']}-{full['away_score']} {full['away_team']}</b>",
        f"Status: {full['status']} | {full['date']} {full.get('time','')}",
        f"Tournament: {full.get('tournament','')}",
        f"Players with stats: {len(ps) // 2}",
        f"Players who played: {len(played)}",
        f"Events: {len(events)}",
        "",
    ]
    if events[:5]:
        lines.append("<b>Events:</b>")
        for e in events[:5]:
            lines.append(f"  {e.get('minute','')}' {e['type']} — {e.get('player','')} ({e.get('team','')})")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("recalculate"))
async def cmd_recalculate(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    # Accept: /recalculate 3  OR  /recalculate GW 3  OR  /recalculate GW3
    gw_id = None
    for p in parts[1:]:
        p = p.upper().replace("GW", "").strip()
        if p.isdigit():
            gw_id = int(p)
            break
    if not gw_id:
        await message.answer("Usage: /recalculate 3  (or /recalculate GW3)")
        return
    await message.answer(f"🔄 Recalculating gameweek {gw_id}...")

    # Get all processed matches for this gameweek
    gw = await sheets.get_gameweek(gw_id)
    if not gw:
        await message.answer("❌ Gameweek not found.")
        return

    # Find matches on this gameweek's date
    matches_on_date = await sheets.get_recent_matches(days=90)
    FINAL_STATUSES = {"final", "ft", "match finished", "aet", "pen", "finished"}
    gw_matches = [m for m in matches_on_date
                  if m.get("match_date") == gw.get("start_date")
                  and (str(m.get("status","")).lower() in FINAL_STATUSES
                       or m.get("home_score") is not None)]

    if not gw_matches:
        await message.answer("No finished matches found for this gameweek.")
        return

    reprocessed = 0
    from scheduler import award_points
    import football_api as _fapi
    for m in gw_matches:
        mid = m["match_id"]
        # Always fetch fresh data from API for recalculation
        full = await _fapi.fetch_full_match(str(mid))
        if not full:
            await message.answer(f"⚠️ Could not fetch fresh data for match {mid}")
            continue
        full["points_awarded"] = False
        sheets._get_sb().table("match_cache").update(
            {"points_awarded": False}
        ).eq("match_id", mid).execute()
        # Reset all user points for this match before recalculating
        all_users = await sheets.get_all_users()
        for u in all_users:
            uid = int(u["telegram_id"])
            # Delete existing player_match_points for this match
            sheets._get_sb().table("player_match_points").delete().eq(
                "telegram_id", uid).eq("match_id", str(mid)).execute()
            # Subtract previously awarded points (stored in total_points)
            # We can't easily know the exact amount so we reset to 0 for safety
            # Actually: just let award_points upsert handle it, but reset total_points
            # by subtracting the sum of existing points for this match first
        await award_points(full, None)
        reprocessed += 1

    await message.answer(f"✅ Recalculated {reprocessed} matches for gameweek {gw_id}.")
    # Broadcast updated points to all confirmed users
    users = await sheets.get_all_users()
    for u in users:
        uid = int(u["telegram_id"])
        try:
            from registration import _home_text, home_keyboard
            from inline import home_keyboard as hk
            import config as _cfg
            fresh_user = await sheets.get_user(uid)
            if not fresh_user:
                continue
            lang = fresh_user.get("language", "en")
            text = await _home_text(fresh_user, lang)
            from inline import home_keyboard
            from registration import _last_home_msg
            tournament = await sheets.get_tournament()
            kb = home_keyboard(lang, tournament)
            # Delete old home message if tracked
            if uid in _last_home_msg:
                try:
                    await message.bot.delete_message(uid, _last_home_msg[uid])
                except Exception:
                    pass
            sent = await message.bot.send_message(uid, text, parse_mode="HTML", reply_markup=kb)
            _last_home_msg[uid] = sent.message_id
        except Exception as e:
            logger.warning("Could not push home to %s: %s", uid, e)


@router.message(Command("recalculate_all"))
async def cmd_recalculate_all(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await message.answer("🔄 Starting full recalculation across all gameweeks. This may take a while...")

    all_matches = await sheets.get_recent_matches(days=365)
    FINAL_STATUSES = {"final", "ft", "match finished", "aet", "pen", "finished"}
    finished_matches = [
        m for m in all_matches
        if str(m.get("status", "")).lower() in FINAL_STATUSES
        or m.get("home_score") is not None
    ]

    if not finished_matches:
        await message.answer("No finished matches found in the database.")
        return

    from scheduler import award_points
    import football_api as _fapi

    total_matches = len(finished_matches)
    await message.answer(f"📋 Found {total_matches} finished matches. Resetting all points first...")

    # Step 1: Reset total_points for all users to 0 — we will recompute from scratch
    all_users = await sheets.get_all_users()
    for u in all_users:
        sheets._get_sb().table("users").update(
            {"total_points": 0}
        ).eq("telegram_id", u["telegram_id"]).execute()

    # Step 2: Delete ALL player_match_points rows in one shot
    sheets._get_sb().table("player_match_points").delete().neq("telegram_id", 0).execute()

    # Step 3: Reset points_awarded flag on all finished matches
    for m in finished_matches:
        sheets._get_sb().table("match_cache").update(
            {"points_awarded": False}
        ).eq("match_id", m["match_id"]).execute()

    await message.answer("♻️ Points reset. Now recalculating match by match...")

    reprocessed = 0
    failed = 0

    # Step 4: Recalculate match by match — award_points only awards to users
    # who have a confirmation on or before that match's gameweek (carry-forward).
    # Users who joined after a match's gameweek will NOT receive points for it.
    for m in finished_matches:
        mid = m["match_id"]
        full = await _fapi.fetch_full_match(str(mid))
        if not full:
            logger.warning("recalculate_all: could not fetch match %s", mid)
            failed += 1
            continue
        full["points_awarded"] = False
        await award_points(full, None)
        reprocessed += 1

    await message.answer(
        f"✅ Recalculation complete.\n"
        f"Matches processed: {reprocessed}/{total_matches}\n"
        f"Failed to fetch from API: {failed}"
    )

    # Step 5: Push updated home screen to all users
    users = await sheets.get_all_users()
    from registration import _push_home
    for u in users:
        uid = int(u["telegram_id"])
        try:
            fresh_user = await sheets.get_user(uid)
            if not fresh_user:
                continue
            lang = fresh_user.get("language", "en")
            await _push_home(message.bot, uid, fresh_user, lang)
        except Exception as e:
            logger.warning("Could not push home to %s: %s", uid, e)


# ── Admin panel callbacks ─────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:reset_all")
async def cb_reset_all(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="💣 YES, RESET EVERYTHING", callback_data="admin:reset_all_confirm")
    kb.button(text="❌ Cancel",                callback_data="admin:back")
    kb.adjust(1)
    await callback.message.edit_text(
        "⚠️ <b>Are you sure?</b>\n\nThis will delete ALL users, squads, points and matches.",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:reset_all_confirm")
async def cb_reset_all_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await sheets.reset_all()
    await callback.message.edit_text(
        "✅ Full reset complete.",
        reply_markup=admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:msg_user")
async def cb_msg_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "Send: /senduser TELEGRAM_ID YOUR MESSAGE",
        reply_markup=admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "Send: /broadcast YOUR MESSAGE",
        reply_markup=admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:reset_user")
async def cb_reset_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "Send: /resetuser TELEGRAM_ID",
        reply_markup=admin_keyboard()
    )
    await callback.answer()
