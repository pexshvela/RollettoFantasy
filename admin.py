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

/gameweeks
<i>List all gameweeks with dates, deadlines and status.</i>

/setgwstatus ID active|upcoming|finished
<i>Manually update a gameweek status.</i>

━━━━━━━━━━━━━━━━━
⏰ <b>DEADLINES</b>
━━━━━━━━━━━━━━━━━

/setdeadline 2026-04-29 20:00
<i>Set confirmation deadline. Format: YYYY-MM-DD HH:MM (UTC).
Users must confirm squad before this time or score 0.</i>

/cleardeadline
<i>Remove the current deadline (squads can confirm anytime).</i>

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
"""


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


@router.message(Command("gameweeks"))
async def cmd_gameweeks(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    gws = await sheets.get_all_gameweeks()
    if not gws:
        await message.answer("No gameweeks yet. Run /fixtures first.")
        return

    lines = ["📅 <b>Gameweeks:</b>\n"]
    for gw in gws:
        emoji = {"active":"🟢","upcoming":"⏳","finished":"✅"}.get(gw.get("status",""),"❓")
        lines.append(
            f"{emoji} <b>GW {gw['id']}</b>: {gw['name']}\n"
            f"   📅 {gw.get('start_date','')} | ⏰ Deadline: {str(gw.get('deadline',''))[:16]}\n"
            f"   Status: {gw.get('status','')}"
        )
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
    if len(parts) < 3:
        await message.answer("Usage: /setdeadline YYYY-MM-DD HH:MM (UTC)")
        return
    try:
        dt_str = f"{parts[1]}T{parts[2]}:00+00:00"
        datetime.fromisoformat(dt_str)  # validate
        await sheets.set_setting("confirmation_deadline", dt_str)
        await message.answer(
            f"✅ Confirmation deadline set:\n<b>{parts[1]} {parts[2]} UTC</b>\n\n"
            f"Users must confirm squad before this time.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Invalid format: {e}\nUse: /setdeadline 2026-04-29 20:00")


@router.message(Command("cleardeadline"))
async def cmd_cleardeadline(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await sheets.set_setting("confirmation_deadline", None)
    await message.answer("✅ Deadline cleared. Squads can confirm anytime.")


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
    gw_matches = [m for m in matches_on_date
                  if m.get("match_date") == gw.get("start_date") and m.get("status") == "final"]

    if not gw_matches:
        await message.answer("No finished matches found for this gameweek.")
        return

    reprocessed = 0
    from scheduler import award_points
    for m in gw_matches:
        if m.get("player_stats"):
            m["id"] = m["match_id"]
            m["points_awarded"] = False
            sheets._get_sb().table("match_cache").update(
                {"points_awarded": False}
            ).eq("match_id", m["match_id"]).execute()
            await award_points(m, None)
            reprocessed += 1

    await message.answer(f"✅ Recalculated {reprocessed} matches for gameweek {gw_id}.")


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
