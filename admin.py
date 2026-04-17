import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

import config
import sheets
from states import Admin
from translations import t
from inline import (admin_menu_keyboard, admin_confirm_send_keyboard,
                    admin_broadcast_type_keyboard, home_keyboard,
                    reset_type_keyboard, reset_campaign_confirm_keyboard)
from helpers import get_lang

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID


@router.callback_query(F.data == "home:admin")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text(t(lang, "admin_menu"), parse_mode="HTML", reply_markup=admin_menu_keyboard(lang))
    await state.set_state(Admin.menu)
    await callback.answer()


@router.callback_query(F.data == "admin:send_msg", Admin.menu)
async def admin_send_msg(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text(t(lang, "admin_get_id"), parse_mode="HTML")
    await state.set_state(Admin.get_target_id)
    await callback.answer()


@router.message(Admin.get_target_id)
async def admin_get_target(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("Please send a valid numeric Telegram ID.")
        return
    target = await sheets.get_user(target_id)
    if not target:
        user = await sheets.get_user(message.from_user.id)
        lang = await get_lang(message.from_user.id, user)
        await message.answer(t(lang, "admin_user_not_found"), parse_mode="HTML")
        return
    await state.update_data(target_ids=[target_id])
    user = await sheets.get_user(message.from_user.id)
    lang = await get_lang(message.from_user.id, user)
    await message.answer(t(lang, "admin_get_msg"), parse_mode="HTML")
    await state.set_state(Admin.get_message)


@router.callback_query(F.data == "admin:broadcast", Admin.menu)
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text("Choose broadcast target:", parse_mode="HTML", reply_markup=admin_broadcast_type_keyboard(lang))
    await state.set_state(Admin.get_broadcast_ids)
    await callback.answer()


@router.callback_query(F.data == "broadcast:all", Admin.get_broadcast_ids)
async def broadcast_all(callback: CallbackQuery, state: FSMContext):
    all_users = await sheets.get_all_users()
    ids = [int(u["telegram_id"]) for u in all_users if u.get("telegram_id")]
    await state.update_data(target_ids=ids)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text(t(lang, "admin_get_msg"), parse_mode="HTML")
    await state.set_state(Admin.get_broadcast_msg)
    await callback.answer()


@router.callback_query(F.data == "broadcast:ids", Admin.get_broadcast_ids)
async def broadcast_ids(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text(t(lang, "admin_get_bc_ids"), parse_mode="HTML")
    await callback.answer()


@router.message(Admin.get_broadcast_ids)
async def receive_id_list(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    if raw.upper() == "ALL":
        all_users = await sheets.get_all_users()
        ids = [int(u["telegram_id"]) for u in all_users if u.get("telegram_id")]
    else:
        try:
            ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            await message.answer("Invalid IDs.")
            return
    await state.update_data(target_ids=ids)
    user = await sheets.get_user(message.from_user.id)
    lang = await get_lang(message.from_user.id, user)
    await message.answer(t(lang, "admin_get_msg"), parse_mode="HTML")
    await state.set_state(Admin.get_broadcast_msg)


@router.message(Admin.get_message)
@router.message(Admin.get_broadcast_msg)
async def receive_message_content(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(msg_id=message.message_id, msg_chat_id=message.chat.id)
    data = await state.get_data()
    target_ids = data.get("target_ids", [])
    user = await sheets.get_user(message.from_user.id)
    lang = await get_lang(message.from_user.id, user)
    await message.answer(t(lang, "admin_confirm_send", n=len(target_ids)), parse_mode="HTML", reply_markup=admin_confirm_send_keyboard(lang))
    await state.set_state(Admin.confirming_send)


@router.callback_query(F.data == "admin:confirm_yes", Admin.confirming_send)
async def admin_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_ids = data.get("target_ids", [])
    msg_id = data.get("msg_id")
    msg_chat_id = data.get("msg_chat_id")
    sent = 0
    for uid in target_ids:
        try:
            await callback.bot.copy_message(chat_id=uid, from_chat_id=msg_chat_id, message_id=msg_id)
            sent += 1
        except Exception as e:
            logger.warning("Could not send to %s: %s", uid, e)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text(t(lang, "admin_send_done", n=sent), parse_mode="HTML", reply_markup=home_keyboard(lang, callback.from_user.id, False, False))
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin:cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text(t(lang, "admin_menu"), parse_mode="HTML", reply_markup=admin_menu_keyboard(lang))
    await state.set_state(Admin.menu)
    await callback.answer()


@router.callback_query(F.data == "admin:pending", Admin.menu)
async def show_pending(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    pending = await sheets.get_pending()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    if not pending:
        text = t(lang, "pending_empty")
    else:
        lines = [f"🆔 <code>{p.get('telegram_id')}</code> @{p.get('tg_username','N/A')} — <b>{p.get('rolletto_username','N/A')}</b>" for p in pending]
        text = t(lang, "pending_list", list="\n".join(lines))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin:back_menu")
async def admin_back_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text(
        t(lang, "admin_menu"), parse_mode="HTML",
        reply_markup=admin_menu_keyboard(lang)
    )
    await state.set_state(Admin.menu)
    await callback.answer()


# ── Reset panel ───────────────────────────────────────────────────────────────

@router.message(Command("reset"))
@router.callback_query(F.data == "admin:reset")
async def admin_reset_panel(event, state: FSMContext):
    user_id = event.from_user.id
    if not is_admin(user_id):
        if hasattr(event, "answer"):
            await event.answer("Not authorized.", show_alert=True)
        return
    text = (
        "🔄 <b>RESET PANEL</b>\n\n"
        "<b>Reset user(s) by ID</b> — enter one or more Telegram IDs. "
        "Wipes their squad, resets budget to €100M, clears points.\n\n"
        "<b>Full campaign reset</b> — wipes ALL squads, ALL transfers, "
        "resets every user. Players stay registered."
    )
    if hasattr(event, "message"):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=reset_type_keyboard())
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=reset_type_keyboard())
    await state.set_state(Admin.reset_menu)


@router.callback_query(F.data == "reset:by_id", Admin.reset_menu)
async def reset_ask_ids(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    await callback.message.edit_text(
        "📋 Send the Telegram ID(s) to reset.\n\n"
        "One ID or multiple separated by commas:\n"
        "<code>123456789</code>\n"
        "<code>123456789, 987654321</code>",
        parse_mode="HTML"
    )
    await state.set_state(Admin.get_reset_id)
    await callback.answer()


@router.message(Admin.get_reset_id)
async def reset_do_users(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    try:
        ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        await message.answer("❌ Invalid IDs. Send numbers separated by commas.")
        return

    await message.answer(f"⏳ Resetting {len(ids)} user(s)...")
    await sheets.reset_users(ids)

    lines = []
    for tid in ids:
        u = await sheets.get_user(tid)
        name = u.get("rolletto_username", str(tid)) if u else str(tid)
        lines.append(f"✅ <b>{name}</b> (<code>{tid}</code>)")

    await message.answer(
        f"✅ Reset complete!\n\n" + "\n".join(lines) +
        "\n\nBudget: €100M | Squad: cleared | Points: 0",
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data == "reset:campaign", Admin.reset_menu)
async def reset_campaign_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    await callback.message.edit_text(
        "⚠️ <b>FULL CAMPAIGN RESET</b>\n\n"
        "This will:\n"
        "• ❌ Delete <b>ALL squads</b>\n"
        "• ❌ Clear <b>ALL transfers</b>\n"
        "• 💰 Reset <b>ALL budgets</b> to €100M\n"
        "• 📊 Reset <b>ALL points</b> to 0\n"
        "• 🧹 Clear <b>ALL formations & captains</b>\n\n"
        "Users stay registered. <b>This cannot be undone.</b>",
        parse_mode="HTML",
        reply_markup=reset_campaign_confirm_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "reset:campaign_confirm")
async def reset_campaign_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    await callback.message.edit_text("⏳ Resetting campaign...", parse_mode="HTML")
    try:
        await sheets.reset_campaign()
        await callback.message.edit_text(
            "✅ <b>Campaign reset complete!</b>\n\n"
            "All squads deleted, transfers cleared, budgets restored to €100M, points zeroed.\n\n"
            "Users can now rebuild their squads from scratch.",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Reset failed:\n<code>{e}</code>", parse_mode="HTML")
    await state.clear()
    await callback.answer()


async def cmd_promo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Enter the Telegram ID of the user to receive the promo:")
    await state.set_state(Admin.get_promo_id)


@router.message(Admin.get_promo_id)
async def promo_get_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("Invalid ID.")
        return
    target = await sheets.get_user(uid)
    if not target:
        await message.answer("User not found.")
        return
    await state.update_data(promo_target_id=uid)
    await message.answer("Enter the promo code to send:")
    await state.set_state(Admin.get_promo_code)


@router.message(Admin.get_promo_code)
async def promo_get_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    code = message.text.strip()
    data = await state.get_data()
    uid = data.get("promo_target_id")
    user = await sheets.get_user(message.from_user.id)
    lang = await get_lang(message.from_user.id, user)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Yes, send", callback_data=f"promo_send:{uid}:{code}")
    kb.button(text="❌ Cancel", callback_data="admin:cancel")
    kb.adjust(2)
    await message.answer(t(lang, "promo_confirm", code=code, uid=uid), parse_mode="HTML", reply_markup=kb.as_markup())
    await state.set_state(Admin.confirming_send)


@router.callback_query(F.data.startswith("promo_send:"))
async def send_promo(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    parts = callback.data.split(":", 2)
    uid, code = int(parts[1]), parts[2]
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    try:
        await callback.bot.send_message(uid, t("en", "promo_sent", code=code), parse_mode="HTML")
        await callback.message.edit_text(t(lang, "promo_done"), parse_mode="HTML")
    except Exception as e:
        await callback.message.edit_text(f"❌ Failed to send: {e}")
    await state.clear()
    await callback.answer()


# ── API Test Commands ─────────────────────────────────────────────────────────

@router.message(Command("testapi"))
async def cmd_testapi(message: Message, state: FSMContext):
    """Admin only — fetch live UCL scores and show raw result."""
    if not is_admin(message.from_user.id):
        return

    await message.answer("🔄 Fetching UCL scores from API...")

    try:
        from football_api import get_scores
        matches = await get_scores()

        if not matches:
            await message.answer(
                "⚠️ API returned 0 matches.\n\n"
                "Possible reasons:\n"
                "• No UCL matches today\n"
                "• API key wrong/expired\n"
                "• API response format changed\n\n"
                "Use /testraw to see the raw API response."
            )
            return

        lines = [f"✅ <b>API working — {len(matches)} match(es) found:</b>\n"]
        for m in matches:
            status_emoji = {"final": "✅", "in_progress": "🔴", "scheduled": "⏳"}.get(m["status"], "❓")
            lines.append(
                f"{status_emoji} <b>{m['homeTeam']}</b> {m['homeScore']} - "
                f"{m['awayScore']} <b>{m['awayTeam']}</b>\n"
                f"   Status: <code>{m['status']}</code> | ID: <code>{m['id']}</code>"
            )

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


@router.message(Command("testraw"))
async def cmd_testraw(message: Message, state: FSMContext):
    """Admin only — show raw API response for debugging."""
    if not is_admin(message.from_user.id):
        return

    await message.answer("🔄 Fetching raw API response...")

    try:
        import aiohttp
        import config

        headers = {
            "x-rapidapi-host": config.API_FOOTBALL_HOST,
            "x-rapidapi-key": config.API_FOOTBALL_KEY,
        }
        url = f"{config.API_FOOTBALL_BASE}/scores"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                status = resp.status
                text = await resp.text()

        # Truncate if too long for Telegram
        preview = text[:3000] + ("..." if len(text) > 3000 else "")
        await message.answer(
            f"📡 <b>Raw API response</b>\n"
            f"URL: <code>{url}</code>\n"
            f"HTTP Status: <code>{status}</code>\n\n"
            f"<pre>{preview}</pre>",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


@router.message(Command("testplayer"))
async def cmd_testplayer(message: Message, state: FSMContext):
    """Admin only — test fetching a specific player by ESPN ID.
    Usage: /testplayer 193232  (Alisson's ESPN ID)
    """
    if not is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer(
            "Usage: <code>/testplayer &lt;espn_id&gt;</code>\n\n"
            "Example: <code>/testplayer 193232</code> (Alisson)\n\n"
            "<b>Key player IDs to test:</b>\n"
            "193232 — Alisson\n"
            "199096 — Mbappé\n"
            "224604 — Bellingham\n"
            "291721 — Saka\n"
            "255996 — Haaland",
            parse_mode="HTML"
        )
        return

    try:
        espn_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid ID — must be a number.")
        return

    await message.answer(f"🔄 Fetching player <code>{espn_id}</code>...", parse_mode="HTML")

    try:
        import aiohttp
        import config

        headers = {
            "x-rapidapi-host": config.API_FOOTBALL_HOST,
            "x-rapidapi-key": config.API_FOOTBALL_KEY,
        }
        url = f"{config.API_FOOTBALL_BASE}/athlete/bio"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                   params={"playerId": str(espn_id)},
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp:
                status = resp.status
                text = await resp.text()

        preview = text[:2500] + ("..." if len(text) > 2500 else "")
        await message.answer(
            f"📡 <b>Player {espn_id} — HTTP {status}</b>\n\n"
            f"<pre>{preview}</pre>",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


@router.message(Command("scores"))
async def cmd_scores(message: Message, state: FSMContext):
    """Admin only — fetch all UCL scores the API returns, optionally filter by date.
    Usage: /scores           → all recent matches
           /scores 2026-04-15 → filter to that date
    """
    if not is_admin(message.from_user.id):
        return

    from datetime import date, timedelta
    parts = message.text.strip().split()
    filter_date = parts[1] if len(parts) >= 2 else None

    label = f"for <code>{filter_date}</code>" if filter_date else "(all recent)"
    await message.answer(f"🔄 Fetching UCL scores {label}...", parse_mode="HTML")

    try:
        import aiohttp
        import config

        headers = {
            "x-rapidapi-host": config.API_FOOTBALL_HOST,
            "x-rapidapi-key": config.API_FOOTBALL_KEY,
        }

        raw_text = ""
        all_events = []

        async with aiohttp.ClientSession() as session:
            # This API returns all recent/live scores with no date filter needed
            url = f"{config.API_FOOTBALL_BASE}/scores"
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp:
                http_status = resp.status
                raw_text = await resp.text()

                if http_status == 200:
                    import json
                    data = json.loads(raw_text)
                    all_events = (
                        data.get("events") or
                        data.get("matches") or
                        data.get("fixtures") or
                        (data if isinstance(data, list) else [])
                    )

        if http_status != 200:
            await message.answer(
                f"❌ API returned HTTP <code>{http_status}</code>\n\n"
                f"Raw: <pre>{raw_text[:500]}</pre>\n\n"
                f"Try /testraw for full details.",
                parse_mode="HTML"
            )
            return

        if not all_events:
            await message.answer(
                f"⚠️ API returned HTTP 200 but no matches in response.\n\n"
                f"Raw preview: <pre>{raw_text[:800]}</pre>\n\n"
                f"Send this to the developer — the response format needs updating.",
                parse_mode="HTML"
            )
            return

        # Client-side date filter
        if filter_date:
            filtered = [m for m in all_events
                        if filter_date in str(m.get("date", "") or m.get("gameDate", "") or "")]
            if not filtered:
                await message.answer(
                    f"⚠️ Got {len(all_events)} match(es) from API but none matched date <code>{filter_date}</code>.\n\n"
                    f"Showing ALL matches instead — check the dates below:",
                    parse_mode="HTML"
                )
                filtered = all_events
        else:
            filtered = all_events

        lines = [f"📅 <b>UCL Matches ({len(filtered)} found):</b>\n"]
        for m in filtered[:15]:  # cap at 15 to avoid Telegram message limit
            try:
                competitors = []
                if "competitions" in m:
                    competitors = m["competitions"][0].get("competitors", [])
                elif "homeTeam" in m:
                    home_name = m.get("homeTeam", {}).get("name") or m.get("homeTeam", "?")
                    away_name = m.get("awayTeam", {}).get("name") or m.get("awayTeam", "?")
                    score = f"{m.get('homeScore','?')} - {m.get('awayScore','?')}"
                    match_date = str(m.get("date", ""))[:10]
                    status = m.get("status", "?")
                    lines.append(f"⚽ <b>{home_name}</b> {score} <b>{away_name}</b> <i>({status}) {match_date}</i>")
                    continue

                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                home_name = home.get("team", {}).get("displayName", "?")
                away_name = away.get("team", {}).get("displayName", "?")
                home_score = home.get("score", "?")
                away_score = away.get("score", "?")
                status = m.get("status", {}).get("type", {}).get("description", "?")
                match_date = str(m.get("date", ""))[:10]
                lines.append(
                    f"⚽ <b>{home_name}</b> {home_score} - {away_score} <b>{away_name}</b>"
                    f" <i>({status}) {match_date}</i>"
                )
            except Exception as ex:
                lines.append(f"• {m.get('name', str(m)[:60])}")

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


@router.message(Command("testflash"))
async def cmd_testflash(message: Message, state: FSMContext):
    """Test FlashScore API with the two confirmed endpoints."""
    if not is_admin(message.from_user.id):
        return

    import aiohttp, config
    headers = {
        "x-rapidapi-host": "flashscore4.p.rapidapi.com",
        "x-rapidapi-key":  config.API_FOOTBALL_KEY,
        "Content-Type": "application/json",
    }
    await message.answer("🔄 Testing FlashScore API...")

    # Test match details (known working match_id from RapidAPI docs)
    test_id = "GCxZ2uHc"
    async with aiohttp.ClientSession() as session:
        for label, url in [
            ("Match Details", f"https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/details?match_id={test_id}"),
            ("Player Stats",  f"https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/match/player-stats?match_id={test_id}"),
        ]:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                status = resp.status
                text = await resp.text()
            await message.answer(
                f"📡 <b>{label}</b>\nHTTP: <code>{status}</code>\n<pre>{text[:1200]}</pre>",
                parse_mode="HTML"
            )


@router.message(Command("testflash_search"))
async def cmd_testflash_search(message: Message, state: FSMContext):
    """Discover UCL tournament ID on FlashScore."""
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔄 Searching for UCL tournament ID...")
    try:
        results = await __import__('football_api').discover_ucl_id()
        for ep, r in results.items():
            await message.answer(
                f"<code>{ep}</code>\nHTTP {r['status']}\n<pre>{r['preview'] or 'empty'}</pre>",
                parse_mode="HTML"
            )
    except Exception as e:
        await message.answer(f"❌ {e}")


@router.message(Command("testmatch"))
async def cmd_testmatch(message: Message, state: FSMContext):
    """Test fetching details for a specific FlashScore match ID.
    Usage: /testmatch GCxZ2uHc
    """
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/testmatch &lt;match_id&gt;</code>", parse_mode="HTML")
        return
    mid = parts[1]
    await message.answer(f"🔄 Fetching match <code>{mid}</code>...", parse_mode="HTML")
    try:
        from football_api import get_match_details, get_player_stats
        details = await get_match_details(mid)
        stats   = await get_player_stats(mid)
        await message.answer(
            f"<b>Match Details:</b>\n<pre>{str(details)[:1000]}</pre>",
            parse_mode="HTML"
        )
        await message.answer(
            f"<b>Player Stats ({len(stats or {})} players):</b>\n<pre>{str(stats)[:1000]}</pre>",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ {e}")


# ── Manual match management ───────────────────────────────────────────────────

@router.message(Command("addmatch"))
async def cmd_addmatch(message: Message, state: FSMContext):
    """
    Admin — manually add a UCL match by FlashScore ID.
    Get match ID from flashscore.com URL:
      https://www.flashscore.com/match/AbCdEfGh/ → ID = AbCdEfGh

    Usage: /addmatch AbCdEfGh
    Bot fetches details + player stats, saves to cache, awards points to all users.
    """
    if not is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer(
            "📖 <b>How to add a UCL match:</b>\n\n"
            "1. Go to <a href='https://www.flashscore.com'>flashscore.com</a>\n"
            "2. Find the UCL match\n"
            "3. Copy the 8-char ID from the URL:\n"
            "   <code>flashscore.com/match/<b>AbCdEfGh</b>/</code>\n"
            "4. Send: <code>/addmatch AbCdEfGh</code>\n\n"
            "Bot will automatically:\n"
            "• Fetch scores + player stats\n"
            "• Calculate & award points to all users\n"
            "• Broadcast match result",
            parse_mode="HTML", disable_web_page_preview=True
        )
        return

    match_id = parts[1].strip()
    msg = await message.answer(f"🔄 Fetching match <code>{match_id}</code>...", parse_mode="HTML")

    try:
        from football_api import fetch_full_match
        match = await fetch_full_match(match_id)

        if not match:
            await msg.edit_text(
                f"❌ Could not fetch match <code>{match_id}</code>\n\n"
                f"Check the ID is correct (from flashscore.com URL) and try again.",
                parse_mode="HTML"
            )
            return

        await msg.edit_text(
            f"✅ Match found:\n\n"
            f"⚽ <b>{match['home_team']} {match['home_score']} - "
            f"{match['away_score']} {match['away_team']}</b>\n"
            f"📅 {match['date']} | {match['status']}\n"
            f"🏆 {match.get('tournament', 'Unknown tournament')}\n\n"
            f"Found {len(match.get('player_stats') or {})} players\n"
            f"Found {len(match.get('events') or [])} events\n\n"
            f"⏳ Processing points for all users...",
            parse_mode="HTML"
        )

        # Save to cache
        await sheets.save_match_cache(match)

        # Award points if match is finished
        if match["status"] == "final" and match.get("player_stats"):
            from scheduler import award_points
            await award_points(match, message.bot)
            await message.answer(
                f"✅ <b>Done!</b> Points awarded to all users.\n"
                f"Users have been notified.",
                parse_mode="HTML"
            )
        elif match["status"] != "final":
            await message.answer(
                f"⚠️ Match is not finished yet (status: {match['status']}).\n"
                f"Match saved to cache. Run /addmatch again after it ends.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"⚠️ Match saved but no player stats found.\n"
                f"Try /addmatch {match_id} again in a few minutes.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error("addmatch error: %s", e)
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


@router.message(Command("listmatches"))
async def cmd_listmatches(message: Message, state: FSMContext):
    """Admin — list all cached UCL matches."""
    if not is_admin(message.from_user.id):
        return

    matches = await sheets.get_recent_matches(days=60)  # show last 60 days
    if not matches:
        await message.answer("No matches in cache yet. Use /addmatch to add UCL matches.")
        return

    lines = ["📋 <b>Cached matches:</b>\n"]
    for m in matches:
        awarded = "✅" if m.get("points_awarded") else "⏳"
        lines.append(
            f"{awarded} <code>{m['match_id']}</code> "
            f"| {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']} "
            f"| {m.get('match_date','?')}"
        )
    lines.append(
        "\n✅ = points awarded | ⏳ = pending\n"
        "Use /addmatch <id> to add or reprocess a match"
    )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("fixmatch"))
async def cmd_fixmatch(message: Message, state: FSMContext):
    """
    Admin — reprocess a match that had wrong stats.
    Usage: /fixmatch AbCdEfGh
    Resets points_awarded flag and re-awards points.
    """
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/fixmatch &lt;match_id&gt;</code>", parse_mode="HTML")
        return

    match_id = parts[1]
    await message.answer(f"🔄 Reprocessing match <code>{match_id}</code>...", parse_mode="HTML")
    try:
        from football_api import fetch_full_match
        from scheduler import award_points
        match = await fetch_full_match(match_id)
        if not match:
            await message.answer("❌ Could not fetch match.")
            return
        match["points_awarded"] = False
        await sheets.save_match_cache(match)
        if match["status"] == "final" and match.get("player_stats"):
            await award_points(match, message.bot)
            await message.answer("✅ Reprocessed. Points re-awarded to all users.")
        else:
            await message.answer(f"⚠️ Match status: {match['status']}. No points awarded.")
    except Exception as e:
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


# ── Match watchlist ───────────────────────────────────────────────────────────

@router.message(Command("schedulematch"))
async def cmd_schedulematch(message: Message, state: FSMContext):
    """
    Add match ID(s) to watchlist. Bot checks every 5 min and auto-processes when finished.
    Get IDs from flashscore.com URLs: flashscore.com/match/AbCdEfGh/

    Usage:
      /schedulematch AbCdEfGh
      /schedulematch AbCdEfGh XyZw1234   (multiple at once)
    """
    if not is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()[1:]
    if not parts:
        await message.answer(
            "📋 <b>Schedule match(es) for auto-processing:</b>\n\n"
            "1. Go to <b>flashscore.com</b>\n"
            "2. Find the UCL match → copy ID from URL:\n"
            "   <code>flashscore.com/match/<b>AbCdEfGh</b>/</code>\n\n"
            "3. Send: <code>/schedulematch AbCdEfGh</code>\n"
            "   Multiple: <code>/schedulematch ID1 ID2 ID3</code>\n\n"
            "Bot checks every 5 min — when match finishes:\n"
            "✅ Fetches stats → awards points → broadcasts result\n\n"
            "View watchlist: /watchlist\n"
            "Cancel a match: /unwatch ID",
            parse_mode="HTML", disable_web_page_preview=True
        )
        return

    added = []
    for mid in parts:
        mid = mid.strip()
        if not mid:
            continue
        await sheets.add_to_watchlist(mid)
        added.append(f"<code>{mid}</code>")

    await message.answer(
        f"✅ Added {len(added)} match(es) to watchlist:\n"
        + "\n".join(added) +
        "\n\nBot will check every 5 min and auto-process when finished.",
        parse_mode="HTML"
    )


@router.message(Command("watchlist"))
async def cmd_watchlist(message: Message, state: FSMContext):
    """Show current match watchlist."""
    if not is_admin(message.from_user.id):
        return

    watchlist = await sheets.get_watchlist()
    if not watchlist:
        await message.answer(
            "📋 Watchlist is empty.\n\n"
            "Add matches with: /schedulematch ID1 ID2"
        )
        return

    lines = [f"📋 <b>Watchlist ({len(watchlist)} match(es)):</b>\n"]
    for w in watchlist:
        lines.append(f"⏳ <code>{w['match_id']}</code> — added {str(w.get('added_at',''))[:10]}")

    lines.append("\nBot checks every 5 min automatically.")
    lines.append("Remove: /unwatch ID")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("unwatch"))
async def cmd_unwatch(message: Message, state: FSMContext):
    """Remove a match from watchlist."""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/unwatch &lt;match_id&gt;</code>", parse_mode="HTML")
        return
    mid = parts[1]
    await sheets.remove_from_watchlist(mid)
    await message.answer(f"✅ Removed <code>{mid}</code> from watchlist.", parse_mode="HTML")


# ── Admin Commands Reference ──────────────────────────────────────────────────

ADMIN_COMMANDS = """📖 <b>ADMIN COMMANDS REFERENCE</b>

━━━━━━━━━━━━━━━━━━━━
⚽ <b>MATCH MANAGEMENT</b>
━━━━━━━━━━━━━━━━━━━━

/schedulematch ID1 ID2
<i>Add match IDs to watchlist at start of match day.
Bot checks every 5 min, auto-awards points when match finishes.
Get IDs from flashscore.com/match/<b>ID</b>/</i>

/watchlist
<i>Show all matches currently being watched.</i>

/unwatch ID
<i>Remove a match from watchlist.</i>

/addmatch ID
<i>Manually add & process an already-finished match.
Use when you forgot to schedule it beforehand.</i>

/fixmatch ID
<i>Reprocess a match (reset points_awarded and re-award).
Use if stats were wrong the first time.</i>

/listmatches
<i>Show all cached matches (last 60 days) with their status.</i>

━━━━━━━━━━━━━━━━━━━━
🔄 <b>CAMPAIGN / USERS</b>
━━━━━━━━━━━━━━━━━━━━

/reset
<i>Open reset panel:
• Reset specific user(s) by Telegram ID
• Full campaign reset (wipes all squads, points, transfers)</i>

/promo
<i>Send a promo code to a specific user by Telegram ID.</i>

━━━━━━━━━━━━━━━━━━━━
📨 <b>MESSAGING</b>
━━━━━━━━━━━━━━━━━━━━

<b>Message User</b> (via Admin Panel button)
<i>Send any message to a single user by Telegram ID.
Supports text, photos, videos — no forwarded header.</i>

<b>Broadcast</b> (via Admin Panel button)
<i>Send a message to all users or a list of IDs.</i>

━━━━━━━━━━━━━━━━━━━━
⚙️ <b>TOURNAMENT FILTER</b>
━━━━━━━━━━━━━━━━━━━━

/settournaments ucl
<i>Set tournament filter. Bot only broadcasts/scans these.
Shortcuts: ucl, pl, wc, el, ecl, laliga, seriea, bundesliga, ligue1
Multiple: /settournaments ucl pl el
Custom: /settournaments custom my-keyword</i>

/tournaments
<i>Show current active tournament filter.</i>

━━━━━━━━━━━━━━━━━━━━
🔬 <b>API TESTING</b>
━━━━━━━━━━━━━━━━━━━━

/testflash
<i>Test FlashScore API with example match. Shows raw JSON.</i>

/testmatch ID
<i>Fetch & parse a specific match. Shows what bot extracts.</i>

/testplayer ESPN_ID
<i>Fetch a player by ESPN ID to verify mapping.</i>

/testraw
<i>Show raw /scores API response for debugging.</i>"""


@router.callback_query(F.data == "admin:commands")
async def show_admin_commands(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Back to Admin", callback_data="admin:back_menu")
    kb.adjust(1)
    await callback.message.edit_text(
        ADMIN_COMMANDS,
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.message(Command("rawmatch"))
async def cmd_rawmatch(message: Message, state: FSMContext):
    """Show ALL keys in match details response to find score field."""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/rawmatch &lt;match_id&gt;</code>", parse_mode="HTML")
        return
    mid = parts[1]
    import aiohttp, config
    headers = {
        "x-rapidapi-host": "flashscore4.p.rapidapi.com",
        "x-rapidapi-key":  config.API_FOOTBALL_KEY,
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/details",
            headers=headers, params={"match_id": mid},
            timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            raw = await resp.json()

    # Show just the top-level keys and their values (not nested dicts)
    lines = [f"🔑 <b>Top-level keys for {mid}:</b>\n"]
    for k, v in raw.items():
        if isinstance(v, dict):
            lines.append(f"<code>{k}</code>: {list(v.keys())}")
        elif isinstance(v, list):
            lines.append(f"<code>{k}</code>: list[{len(v)}]")
        else:
            lines.append(f"<code>{k}</code>: <b>{v}</b>")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("testincidents"))
async def cmd_testincidents(message: Message, state: FSMContext):
    """Try all known incident endpoints for a match."""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    mid = parts[1] if len(parts) >= 2 else "zXC8QVx3"
    import aiohttp, config
    headers = {
        "x-rapidapi-host": "flashscore4.p.rapidapi.com",
        "x-rapidapi-key":  config.API_FOOTBALL_KEY,
        "Content-Type": "application/json",
    }
    endpoints = [
        f"/api/flashscore/v2/matches/match/incidents?match_id={mid}",
        f"/api/flashscore/v2/matches/incidents?match_id={mid}",
        f"/api/flashscore/v2/matches/match/summary?match_id={mid}",
        f"/api/flashscore/v2/matches/summary?match_id={mid}",
        f"/api/flashscore/v2/matches/match/events?match_id={mid}",
        f"/api/flashscore/v2/matches/events?match_id={mid}",
        f"/api/flashscore/v2/matches/match/timeline?match_id={mid}",
    ]
    async with aiohttp.ClientSession() as s:
        for ep in endpoints:
            url = f"https://flashscore4.p.rapidapi.com{ep}"
            async with s.get(url, headers=headers,
                             timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                if status == 200:
                    text = await resp.text()
                    preview = text[:600]
                else:
                    preview = f"HTTP {status}"
            await message.answer(
                f"<code>{ep.split('?')[0]}</code>\n{preview}",
                parse_mode="HTML"
            )


@router.message(Command("testlineup"))
async def cmd_testlineup(message: Message, state: FSMContext):
    """Test lineups + list-by-date endpoints."""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    mid = parts[1] if len(parts) >= 2 else "zXC8QVx3"

    import aiohttp, config, json
    from datetime import date
    headers = {
        "x-rapidapi-host": "flashscore4.p.rapidapi.com",
        "x-rapidapi-key":  config.API_FOOTBALL_KEY,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as s:
        # Test lineups
        url = f"https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/match/lineups"
        async with s.get(url, headers=headers, params={"match_id": mid},
                         timeout=aiohttp.ClientTimeout(total=15)) as resp:
            status = resp.status
            text = await resp.text()
        await message.answer(
            f"📋 <b>Lineups HTTP {status}</b>\n<pre>{text[:2000]}</pre>",
            parse_mode="HTML"
        )

        # Test list-by-date
        today = date.today().isoformat()
        url2 = f"https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/list-by-date"
        async with s.get(url2, headers=headers,
                         params={"sport_id": "1", "date": today, "timezone": "Europe/Berlin"},
                         timeout=aiohttp.ClientTimeout(total=15)) as resp2:
            status2 = resp2.status
            text2 = await resp2.text()
        await message.answer(
            f"📅 <b>List-by-date ({today}) HTTP {status2}</b>\n<pre>{text2[:2000]}</pre>",
            parse_mode="HTML"
        )


# ── Tournament filter ─────────────────────────────────────────────────────────

# SofaScore uniqueTournament IDs
KNOWN_TOURNAMENTS = {
    "ucl":        ("Champions League",    7),
    "pl":         ("Premier League",      17),
    "laliga":     ("La Liga",             8),
    "bundesliga": ("Bundesliga",          35),
    "seriea":     ("Serie A",             23),
    "ligue1":     ("Ligue 1",             34),
    "el":         ("Europa League",       679),
    "ecl":        ("Conference League",   17015),
    "wc":         ("World Cup",           16),
    "cl_asia":    ("AFC Champions League",NA := None),  # not available
}
# Remove None entries
KNOWN_TOURNAMENTS = {k: v for k, v in KNOWN_TOURNAMENTS.items() if v[1] is not None}


@router.message(Command("settournaments"))
async def cmd_settournaments(message: Message, state: FSMContext):
    """
    Set which tournaments to auto-scan and broadcast results for.

    Usage:
      /settournaments ucl              → Champions League only
      /settournaments ucl pl           → UCL + Premier League
      /settournaments ucl el ecl       → UCL + Europa + Conference
      /settournaments custom champions-league premier-league  → custom keywords

    Shortcuts: ucl, pl, wc, el, ecl, laliga, seriea, bundesliga, ligue1
    """
    if not is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()[1:]
    if not parts:
        # Show current setting + available options
        current = await sheets.get_tournament_keywords()
        lines = [
            "🏆 <b>Tournament Filter</b>\n",
            f"Current keywords: {', '.join(f'<code>{k}</code>' for k in current)}\n",
            "<b>Available shortcuts:</b>",
        ]
        for code, (name, keywords) in KNOWN_TOURNAMENTS.items():
            lines.append(f"  <code>{code}</code> → {name}")
        lines.append(
            "\n<b>Usage:</b>\n"
            "<code>/settournaments ucl</code>\n"
            "<code>/settournaments ucl pl</code>\n"
            "<code>/settournaments ucl el ecl</code>\n"
            "<code>/settournaments custom my-keyword</code>"
        )
        await message.answer("\n".join(lines), parse_mode="HTML")
        return

    # Custom keywords mode
    if parts[0] == "custom":
        keywords = parts[1:]
        if not keywords:
            await message.answer("❌ Provide at least one keyword after 'custom'.")
            return
        # Try to parse as numeric IDs
        try:
            ids = [int(x) for x in parts[1:]]
            await sheets.set_setting("tournament_ids", ids)
            await message.answer(f"✅ Custom tournament IDs set: {ids}")
            return
        except ValueError:
            pass
        await sheets.set_setting("tournament_ids", [])
        await message.answer("❌ After 'custom' provide numeric SofaScore tournament IDs.")
        return

    # Shortcut mode
    ids = []
    names = []
    unknown = []
    for code in parts:
        code_lower = code.lower()
        if code_lower in KNOWN_TOURNAMENTS:
            name, tid = KNOWN_TOURNAMENTS[code_lower]
            ids.append(tid)
            names.append(name)
        else:
            unknown.append(code)

    if unknown:
        await message.answer(
            f"❌ Unknown shortcuts: {', '.join(unknown)}\n\n"
            f"Use /settournaments to see available options.",
            parse_mode="HTML"
        )
        return

    if not ids:
        await message.answer("❌ No valid tournaments selected.")
        return

    await sheets.set_setting("tournament_ids", ids)
    id_list = ", ".join(str(i) for i in ids)
    await message.answer(
        f"✅ <b>Tournament filter updated:</b>\n\n"
        + "\n".join(f"  🏆 {n}" for n in names) +
        f"\n\nSofaScore IDs: <code>{id_list}</code>\n"
        f"Bot will now auto-scan and broadcast results for these only.",
        parse_mode="HTML"
    )


@router.message(Command("tournaments"))
async def cmd_tournaments(message: Message, state: FSMContext):
    """Show current tournament filter."""
    if not is_admin(message.from_user.id):
        return
    current = await sheets.get_tournament_keywords()
    await message.answer(
        f"🏆 <b>Active tournament filter:</b>\n\n"
        + "\n".join(f"  • <code>{k}</code>" for k in current) +
        f"\n\nChange with: /settournaments ucl pl el",
        parse_mode="HTML"
    )


@router.message(Command("cleancache"))
async def cmd_cleancache(message: Message, state: FSMContext):
    """Remove non-UCL matches from match_cache that don't match active keywords."""
    if not is_admin(message.from_user.id):
        return

    keywords = await sheets.get_tournament_keywords()
    all_matches = await sheets.get_recent_matches(days=60)

    def _t_matches(tn, tu, kws):
        tn, tu = tn.lower(), tu.lower()
        for kw in kws:
            kl = kw.lower()
            kw_w = kl.replace("-"," ").replace("_"," ")
            is_cl = ("champions" in kl and "league" in kw_w)
            if kl in tn or kw_w in tn:
                if is_cl:
                    if "uefa" in tn or any(x in tu for x in ["europe","uefa"]):
                        return True
                else:
                    return True
        return False

    to_delete = [
        m["match_id"] for m in all_matches
        if not _t_matches(
            m.get("tournament") or "",
            m.get("tournament_url") or "",
            keywords
        )
    ]

    if not to_delete:
        await message.answer("✅ Cache is already clean — no non-matching matches found.")
        return

    sb = sheets._get_sb()
    for mid in to_delete:
        try:
            sb.table("match_cache").delete().eq("match_id", mid).execute()
        except Exception as e:
            logger.error("cleancache delete error %s: %s", mid, e)

    await message.answer(
        f"✅ Removed <b>{len(to_delete)}</b> non-matching match(es) from cache.\n\n"
        f"Active filter: {', '.join(f'<code>{k}</code>' for k in keywords)}",
        parse_mode="HTML"
    )


@router.message(Command("debugmatch"))
async def cmd_debugmatch(message: Message, state: FSMContext):
    """Debug why a match can't be fetched."""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: /debugmatch <match_id>")
        return
    mid = parts[1]
    import aiohttp, config, json
    headers = {
        "x-rapidapi-host": "flashscore4.p.rapidapi.com",
        "x-rapidapi-key":  config.API_FOOTBALL_KEY,
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as s:
        url = "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/details"
        async with s.get(url, headers=headers, params={"match_id": mid},
                         timeout=aiohttp.ClientTimeout(total=15)) as resp:
            status = resp.status
            text = await resp.text()
    await message.answer(
        f"HTTP: <code>{status}</code>\n<pre>{text[:3000]}</pre>",
        parse_mode="HTML"
    )


@router.message(Command("testsportapi"))
async def cmd_testsportapi(message: Message, state: FSMContext):
    """Test SportAPI7 — shows recent/live/upcoming UCL matches."""
    if not is_admin(message.from_user.id):
        return
    from datetime import date, timedelta
    await message.answer("🔄 Testing SportAPI7...")
    try:
        from football_api import get_matches_by_date, get_upcoming_matches
        tournament_ids = await sheets.get_tournament_ids()

        # Check yesterday, today
        found_matches = []
        found_label = ""
        for days_back, label in [(1, "yesterday"), (0, "today")]:
            d = (date.today() - timedelta(days=days_back)).isoformat()
            m = await get_matches_by_date(d, tournament_ids)
            if m:
                found_matches = m
                found_label = label
                break

        if found_matches:
            lines = ["✅ <b>API working! Matches " + found_label + ":</b>\n"]
            for m in found_matches:
                emoji = {"final": "✅", "in_progress": "🔴"}.get(m["status"], "⏳")
                lines.append(
                    emoji + " <b>" + m['home_team'] + "</b> " +
                    str(m['home_score']) + "-" + str(m['away_score']) + " " +
                    "<b>" + m['away_team'] + "</b>\n" +
                    "   📅 " + m['date'] + " | ID: <code>" + m['id'] + "</code>"
                )
        else:
            # No recent matches — find ALL upcoming
            upcoming = await get_upcoming_matches(tournament_ids, days_ahead=90)
            if upcoming:
                from collections import defaultdict
                by_date = defaultdict(list)
                for m in upcoming:
                    by_date[m["date"]].append(m)
                lines = ["\u2705 <b>API working!</b> Upcoming fixtures:\n"]
                for d_str in sorted(by_date.keys()):
                    lines.append("\n<b>" + d_str + "</b>")
                    for m in by_date[d_str]:
                        lines.append(
                            "  " + m["home_team"] + " vs " + m["away_team"] +
                            " | ID: <code>" + m["id"] + "</code>"
                        )
                lines.append("\n\nRun /fixtures to auto-add all to watchlist.")
            else:
                lines = [
                    "\u26a0\ufe0f No matches found.",
                    "Tournament IDs: " + str(tournament_ids),
                ]

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


@router.message(Command("testmatchsport"))
async def cmd_testmatchsport(message: Message, state: FSMContext):
    """Test full match fetch with SportAPI7. Usage: /testmatchsport <event_id>"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/testmatchsport &lt;event_id&gt;</code>", parse_mode="HTML")
        return
    eid = parts[1]
    await message.answer(f"🔄 Fetching event <code>{eid}</code>...", parse_mode="HTML")
    try:
        from football_api import fetch_full_match
        match = await fetch_full_match(eid)
        if not match:
            await message.answer("❌ Could not fetch match.")
            return
        ps = match.get("player_stats") or {}
        ev = match.get("events") or []
        played = match.get("played_ids") or set()
        await message.answer(
            f"✅ <b>{match['home_team']} {match['home_score']}-{match['away_score']} {match['away_team']}</b>\n"
            f"Status: {match['status']} | Date: {match['date']}\n"
            f"Players with stats: {len(ps)}\n"
            f"Players who played: {len(played)}\n"
            f"Events: {len(ev)}\n\n"
            f"<b>Sample events:</b>\n" +
            "\n".join(f"  {e['minute']}' {e['type']} — {e['player']}" for e in ev[:5]),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


@router.message(Command("fixtures"))
async def cmd_fixtures(message: Message, state: FSMContext):
    """
    Show ALL fixtures for active tournament(s) and auto-add future ones to watchlist.
    Usage: /fixtures
    """
    if not is_admin(message.from_user.id):
        return

    await message.answer("🔄 Fetching all tournament fixtures...")

    try:
        from football_api import get_all_tournament_fixtures
        from datetime import date

        tournament_ids = await sheets.get_tournament_ids()
        all_matches = await get_all_tournament_fixtures(tournament_ids)

        if not all_matches:
            await message.answer("⚠️ No fixtures found for active tournaments.")
            return

        today = date.today().isoformat()

        past     = [m for m in all_matches if m["date"] < today]
        today_m  = [m for m in all_matches if m["date"] == today]
        future   = [m for m in all_matches if m["date"] > today]

        # Auto-add unfinished future matches to watchlist
        added_ids = []
        for m in today_m + future:
            if m["status"] != "final":
                await sheets.add_to_watchlist(m["id"])
                added_ids.append(m["id"])

        # Build message
        lines = [f"📋 <b>All Fixtures</b> ({len(all_matches)} matches)\n"]

        if past:
            lines.append("✅ <b>Past results:</b>")
            for m in past[-10:]:  # show last 10
                lines.append(
                    f"  {m['date']}: {m['home_team']} "
                    f"{m['home_score']}-{m['away_score']} "
                    f"{m['away_team']}"
                )

        if today_m:
            lines.append("\n🔴 <b>Today:</b>")
            for m in today_m:
                lines.append(
                    f"  {m['home_team']} vs {m['away_team']} "
                    f"| ID: <code>{m['id']}</code>"
                )

        if future:
            lines.append("\n⏳ <b>Upcoming:</b>")
            for m in future[:15]:  # show next 15
                lines.append(
                    f"  📅 {m['date']}: {m['home_team']} vs {m['away_team']} "
                    f"| ID: <code>{m['id']}</code>"
                )

        if added_ids:
            lines.append(
                f"\n✅ <b>Auto-added {len(added_ids)} match(es) to watchlist.</b>\n"
                f"Bot will process them automatically when they finish."
            )

        # Split message if too long
        text = "\n".join(lines)
        if len(text) > 4000:
            # Send in chunks
            for i in range(0, len(lines), 30):
                chunk = "\n".join(lines[i:i+30])
                await message.answer(chunk, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error("fixtures error: %s", e)
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")


@router.message(Command("testdate"))
async def cmd_testdate(message: Message, state: FSMContext):
    """Test what matches SportAPI7 returns for a specific date.
    Usage: /testdate 2026-04-18
    """
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    from datetime import date, timedelta
    d = parts[1] if len(parts) >= 2 else (date.today() + timedelta(days=1)).isoformat()

    import aiohttp, config
    headers = {
        "X-RapidAPI-Key":  config.API_FOOTBALL_KEY,
        "X-RapidAPI-Host": "sportapi7.p.rapidapi.com",
    }
    await message.answer(f"🔄 Fetching matches for {d}...")
    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"https://sportapi7.p.rapidapi.com/api/v1/sport/football/scheduled-events/{d}",
            headers=headers, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            status = resp.status
            if status != 200:
                await message.answer(f"❌ HTTP {status}")
                return
            data = await resp.json()

    events = data.get("events") or []
    if not events:
        await message.answer(f"No events found for {d}")
        return

    # Group by tournament and show unique tournaments + sample matches
    from collections import defaultdict
    by_tournament = defaultdict(list)
    for e in events:
        t = e.get("tournament") or {}
        ut = t.get("uniqueTournament") or {}
        tid = ut.get("id", "?")
        tname = ut.get("name") or t.get("name") or "?"
        key = f"{tname} (ID:{tid})"
        by_tournament[key].append(e)

    lines = [f"📅 <b>{d}</b> — {len(events)} matches in {len(by_tournament)} tournaments\n"]
    for tname, tevents in sorted(by_tournament.items()):
        lines.append(f"\n<b>{tname}</b> ({len(tevents)} matches)")
        for e in tevents[:2]:
            home = (e.get("homeTeam") or {}).get("name","?")
            away = (e.get("awayTeam") or {}).get("name","?")
            eid  = e.get("id","?")
            lines.append(f"  {home} vs {away} | ID:<code>{eid}</code>")
        if len(tevents) > 2:
            lines.append(f"  ... and {len(tevents)-2} more")

    text = "\n".join(lines)
    # Split if too long
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="HTML")


@router.message(Command("checkdate"))
async def cmd_checkdate(message: Message, state: FSMContext):
    """
    Check what tournaments are available on a specific date.
    Usage: /checkdate 2026-04-19
    Shows tournament IDs so you can use them with /settournaments custom <id>
    """
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        from datetime import date, timedelta
        date_str = (date.today() + __import__('datetime').timedelta(days=1)).isoformat()
    else:
        date_str = parts[1]

    await message.answer(f"🔄 Checking {date_str}...")

    import aiohttp, config
    headers = {
        "X-RapidAPI-Key":  config.API_FOOTBALL_KEY,
        "X-RapidAPI-Host": "sportapi7.p.rapidapi.com",
    }
    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"https://sportapi7.p.rapidapi.com/api/v1/sport/football/scheduled-events/{date_str}",
            headers=headers, timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            if resp.status != 200:
                await message.answer(f"❌ HTTP {resp.status}")
                return
            data = await resp.json()

    events = data.get("events") or []
    # Group by tournament
    tournaments = {}
    for e in events:
        t = e.get("tournament") or {}
        ut = t.get("uniqueTournament") or {}
        tid = ut.get("id")
        tname = ut.get("name") or t.get("name") or "?"
        if tid not in tournaments:
            tournaments[tid] = {"name": tname, "count": 0}
        tournaments[tid]["count"] += 1

    lines = [f"📅 <b>{date_str}</b> — {len(events)} total matches\n",
             "<b>Tournaments found:</b>"]
    for tid, info in sorted(tournaments.items(), key=lambda x: -x[1]["count"])[:20]:
        lines.append(f"  ID <code>{tid}</code> — {info['name']} ({info['count']} matches)")

    lines.append("\nUse: /settournaments custom <id1> <id2>")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("apitest"))
async def cmd_apitest(message: Message, state: FSMContext):
    """Raw test of SportAPI7 with a single date."""
    if not is_admin(message.from_user.id):
        return
    import aiohttp, config, json
    from datetime import date, timedelta

    # Test tomorrow
    date_str = (date.today() + timedelta(days=1)).isoformat()
    await message.answer(f"Testing SportAPI7 for {date_str}...")

    headers = {
        "X-RapidAPI-Key":  config.API_FOOTBALL_KEY,
        "X-RapidAPI-Host": "sportapi7.p.rapidapi.com",
    }
    url = f"https://sportapi7.p.rapidapi.com/api/v1/sport/football/scheduled-events/{date_str}"

    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers,
                         timeout=aiohttp.ClientTimeout(total=20)) as resp:
            status = resp.status
            text = await resp.text()

    await message.answer(
        f"HTTP: <code>{status}</code>\n"
        f"URL: <code>{url}</code>\n"
        f"Key prefix: <code>{config.API_FOOTBALL_KEY[:8]}...</code>\n"
        f"Response preview:\n<pre>{text[:1500]}</pre>",
        parse_mode="HTML"
    )

    # Also show current tournament IDs setting
    t_ids = await sheets.get_tournament_ids()
    await message.answer(f"Active tournament IDs: <code>{t_ids}</code>", parse_mode="HTML")
