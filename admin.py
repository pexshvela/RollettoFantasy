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
    """Admin only — fetch UCL scores for a specific date or yesterday.
    Usage: /scores           → yesterday
           /scores 2026-04-15 → specific date
    """
    if not is_admin(message.from_user.id):
        return

    from datetime import date, timedelta
    parts = message.text.strip().split()

    if len(parts) >= 2:
        date_str = parts[1]
    else:
        date_str = (date.today() - timedelta(days=1)).isoformat()

    await message.answer(f"🔄 Fetching UCL scores for <code>{date_str}</code>...", parse_mode="HTML")

    try:
        import aiohttp
        import config

        headers = {
            "x-rapidapi-host": config.API_FOOTBALL_HOST,
            "x-rapidapi-key": config.API_FOOTBALL_KEY,
        }

        # Try with date param first
        results = []
        async with aiohttp.ClientSession() as session:
            for endpoint, params in [
                ("/scores", {"date": date_str}),
                ("/scores", {"dates": date_str}),
                ("/matches", {"date": date_str}),
            ]:
                url = f"{config.API_FOOTBALL_BASE}{endpoint}"
                async with session.get(url, headers=headers, params=params,
                                       timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw = (data.get("events") or data.get("matches") or
                               (data if isinstance(data, list) else []))
                        if raw:
                            results = raw
                            break
                        # Also try raw response for debugging
                        raw_text = str(data)[:800]
                    else:
                        raw_text = f"HTTP {resp.status}"

        if not results:
            await message.answer(
                f"⚠️ No matches found for <code>{date_str}</code>\n\n"
                f"Last raw response preview:\n<pre>{raw_text}</pre>",
                parse_mode="HTML"
            )
            return

        lines = [f"📅 <b>UCL Results — {date_str}</b>\n"]
        for m in results:
            try:
                # Parse teams and score
                competitors = []
                if "competitions" in m:
                    competitors = m["competitions"][0].get("competitors", [])
                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                home_name = home.get("team", {}).get("displayName", m.get("name", "?"))
                away_name = away.get("team", {}).get("displayName", "?")
                home_score = home.get("score", "?")
                away_score = away.get("score", "?")
                status = m.get("status", {}).get("type", {}).get("description", "?")
                lines.append(f"⚽ <b>{home_name}</b> {home_score} - {away_score} <b>{away_name}</b> <i>({status})</i>")
            except Exception:
                lines.append(f"• {m.get('name', str(m)[:80])}")

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Error: <code>{e}</code>", parse_mode="HTML")
