import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest

import config
import sheets
from states import Registration, Setup, Squad
from translations import t
from inline import lang_keyboard, rules_keyboard, home_keyboard
from helpers import build_home_text, get_lang

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await sheets.get_user(message.from_user.id)

    if user:
        lang = user.get("language", "en")
        squad_data = await sheets.get_squad(message.from_user.id)
        formation = user.get("formation", "")
        submitted = user.get("squad_submitted", "no") == "yes"
        text = build_home_text(lang, user, squad_data)
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=home_keyboard(lang, message.from_user.id, submitted, bool(formation)),
        )
        await state.set_state(Squad.home)
        return

    await message.answer(t("en", "ask_username"), parse_mode="HTML")
    await state.set_state(Registration.waiting_username)


@router.message(Registration.waiting_username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip()
    await state.update_data(rolletto_username=username)

    checking_msg = await message.answer(t("en", "checking"), parse_mode="HTML")
    found = await sheets.check_rolletto_username(username)

    if found:
        await sheets.create_user(
            message.from_user.id,
            username,
            message.from_user.username or "",
        )
        await checking_msg.edit_text(
            t("en", "found_welcome", username=username),
            parse_mode="HTML",
            reply_markup=lang_keyboard(),
        )
        await state.set_state(Setup.selecting_language)
    else:
        await checking_msg.edit_text(
            t("en", "not_found", url=config.ROLLETTO_SIGNUP_URL),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await state.set_state(Registration.waiting_check)


@router.message(Command("check"), Registration.waiting_check)
async def cmd_check(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("rolletto_username", "")

    checking_msg = await message.answer(t("en", "checking"), parse_mode="HTML")
    found = await sheets.check_rolletto_username(username)

    if found:
        await sheets.create_user(
            message.from_user.id,
            username,
            message.from_user.username or "",
        )
        await checking_msg.edit_text(
            t("en", "found_welcome", username=username),
            parse_mode="HTML",
            reply_markup=lang_keyboard(),
        )
        await state.set_state(Setup.selecting_language)
    else:
        from datetime import datetime
        try:
            await message.bot.send_message(
                config.ADMIN_ID,
                t("en", "admin_notify_pending",
                  tg_id=message.from_user.id,
                  tg_username=message.from_user.username or "N/A",
                  rolletto=username,
                  time=datetime.now().strftime("%Y-%m-%d %H:%M")),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Could not notify admin: %s", e)

        await sheets.add_pending(
            message.from_user.id,
            message.from_user.username or "",
            username,
        )
        await checking_msg.edit_text(t("en", "still_not_found"), parse_mode="HTML")


@router.callback_query(F.data.startswith("lang:"), Setup.selecting_language)
async def select_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    await sheets.update_user(callback.from_user.id, language=lang)
    await state.update_data(lang=lang)
    await callback.message.edit_text(
        t(lang, "rules_title"),
        parse_mode="HTML",
        reply_markup=rules_keyboard(lang),
    )
    await state.set_state(Setup.reading_rules)
    await callback.answer()


@router.callback_query(F.data == "rules:accept", Setup.reading_rules)
async def accept_rules(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    user = await sheets.get_user(callback.from_user.id)
    text = build_home_text(lang, user, squad=None)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=home_keyboard(lang, callback.from_user.id, False, False),
    )
    await state.set_state(Squad.home)
    await callback.answer()


@router.callback_query(F.data == "home:back")
async def go_home(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id)
    formation = user.get("formation", "") if user else ""
    submitted = (user.get("squad_submitted", "no") == "yes") if user else False
    text = build_home_text(lang, user, squad_data)
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=home_keyboard(lang, callback.from_user.id, submitted, bool(formation)),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await state.set_state(Squad.home)
    await callback.answer()


@router.callback_query(F.data == "home:rules")
async def show_rules(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    try:
        await callback.message.edit_text(
            t(lang, "rules_title"),
            parse_mode="HTML",
            reply_markup=kb.as_markup(),
            disable_web_page_preview=True,
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()

@router.callback_query(F.data == "home:rules")
async def show_rules(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    await callback.message.edit_text(
        t(lang, "rules_title"),
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()
