"""registration.py — /start, language selection, username verification."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import sheets
import players as pl_module
from states import Registration
from translations import t
from inline import home_keyboard, back_home

logger = logging.getLogger(__name__)
router = Router()


def language_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇬🇧 English",  callback_data="lang:en")
    kb.button(text="🇮🇹 Italiano", callback_data="lang:it")
    kb.button(text="🇫🇷 Français", callback_data="lang:fr")
    kb.button(text="🇪🇸 Español",  callback_data="lang:es")
    kb.adjust(2)
    return kb.as_markup()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid  = message.from_user.id
    user = await sheets.get_user(uid)

    if user:
        # Already registered — go home
        lang = user.get("language", "en")
        tournament = await sheets.get_tournament()
        pl_module.set_active_tournament(tournament)
        await _show_home(message, user, lang)
        return

    await message.answer(
        "🌍 Welcome to <b>Rolletto Fantasy Football!</b>\n\nChoose your language:",
        parse_mode="HTML",
        reply_markup=language_keyboard()
    )
    await state.set_state(Registration.language)


@router.callback_query(Registration.language, F.data.startswith("lang:"))
async def pick_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    await state.update_data(language=lang)
    await callback.message.edit_text(
        t(lang, "enter_username"),
        reply_markup=None
    )
    await state.set_state(Registration.username)
    await callback.answer()


@router.message(Registration.username)
async def enter_username(message: Message, state: FSMContext):
    data     = await state.get_data()
    lang     = data.get("language", "en")
    username = message.text.strip()

    await message.answer(t(lang, "verifying"))

    found = await sheets.verify_username(username)
    if not found:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔄 Try Again", callback_data="reg:retry")
        kb.adjust(1)
        await message.answer(
            t(lang, "not_found", url=sheets.config.ROLLETTO_SIGNUP_URL),
            reply_markup=kb.as_markup()
        )
        return

    # Create user
    uid  = message.from_user.id
    user = await sheets.create_user(uid, username, lang)

    # Set active tournament
    tournament = await sheets.get_tournament()
    pl_module.set_active_tournament(tournament)

    await state.clear()
    await message.answer(
        t(lang, "verified", username=username),
        parse_mode="HTML"
    )
    await _show_home(message, user, lang)


@router.callback_query(F.data == "reg:retry")
async def retry_username(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    await callback.message.edit_text(t(lang, "enter_username"))
    await state.set_state(Registration.username)
    await callback.answer()


@router.callback_query(F.data == "home:back")
async def go_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    if not user:
        await callback.message.edit_text("Please use /start to register. Send /start to begin.")
        await callback.answer()
        return
    lang = user.get("language", "en")
    tournament = await sheets.get_tournament()
    pl_module.set_active_tournament(tournament)
    await _edit_home(callback.message, user, lang)
    await callback.answer()


async def _show_home(message: Message, user: dict, lang: str):
    text = await _home_text(user, lang)
    await message.answer(text, parse_mode="HTML", reply_markup=home_keyboard(lang))


async def _edit_home(message: Message, user: dict, lang: str):
    text = await _home_text(user, lang)
    try:
        await message.edit_text(text, parse_mode="HTML", reply_markup=home_keyboard(lang))
    except Exception:
        await message.answer(text, parse_mode="HTML", reply_markup=home_keyboard(lang))


async def _home_text(user: dict, lang: str) -> str:
    gw = await sheets.get_active_gameweek()
    deadline = await sheets.get_confirmation_deadline()
    confirmed = user.get("confirmed", False)
    pts = user.get("total_points", 0)

    status_parts = []
    if gw:
        status_parts.append(f"📅 Gameweek: <b>{gw['name']}</b>")
    if deadline:
        status_parts.append(f"⏰ Deadline: <b>{deadline[:16]}</b>")
    if confirmed:
        status_parts.append("✅ Squad confirmed")
    else:
        status_parts.append("⚠️ Squad not confirmed")
    status_parts.append(f"🏆 Total points: <b>{pts}</b>")

    status = "\n".join(status_parts)
    return t(lang, "home_title", status=status)


@router.callback_query(F.data == "home:rules")
async def show_rules(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = (user or {}).get("language", "en")
    kb   = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    await callback.message.edit_text(
        t(lang, "rules_title") + "\n" + t(lang, "rules_text"),
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await callback.answer()
