import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

import config
import sheets
from states import Squad
from translations import t
from players import get_player, fmt_price, get_by_position
from inline import (
    formation_keyboard, squad_keyboard, player_list_keyboard,
    confirm_player_keyboard, captain_keyboard, confirm_submit_keyboard,
    home_keyboard, slot_action_keyboard,
)
from helpers import build_squad_visual, build_home_text, get_lang, count_squad_filled

logger = logging.getLogger(__name__)
router = Router()


def _safe_budget(user):
    """Safely parse budget from user dict — handles int/float/string."""
    raw = (user or {}).get("budget_remaining", config.TOTAL_BUDGET)
    try:
        return int(float(raw or config.TOTAL_BUDGET))
    except (ValueError, TypeError):
        return config.TOTAL_BUDGET


def _merge_captain(user, squad_data):
    """Add captain from user record into squad_data so the ⭐ shows in the visual."""
    if squad_data is None:
        squad_data = {}
    captain = (user or {}).get("captain", "")
    if captain:
        squad_data["captain"] = captain
    return squad_data


async def _show_squad(callback, user, squad_data, lang, state):
    """Central helper to display squad view — avoids code duplication."""
    formation = (user or {}).get("formation", "4-3-3") or "4-3-3"
    budget = _safe_budget(user)
    squad_data = _merge_captain(user, squad_data or {})
    visual = build_squad_visual(formation, squad_data)
    text = t(lang, "squad_view", formation=formation,
             budget=fmt_price(budget), visual=visual)
    # Safety: Telegram max is 4096 chars
    if len(text) > 4000:
        text = text[:4000] + "…"
    try:
        await callback.message.edit_text(
            text, parse_mode="HTML",
            reply_markup=squad_keyboard(lang, formation, squad_data),
        )
    except TelegramBadRequest as e:
        err = str(e)
        if "message is not modified" in err:
            pass  # harmless — user tapped same button twice
        elif "MESSAGE_TOO_LONG" in err:
            # Fallback: show just the basics without visual
            fallback = t(lang, "squad_view",
                         formation=formation, budget=fmt_price(budget), visual="[tap a slot to see]")
            await callback.message.edit_text(
                fallback, parse_mode="HTML",
                reply_markup=squad_keyboard(lang, formation, squad_data),
            )
        else:
            raise
    await state.set_state(Squad.viewing_squad)
    await callback.answer()


@router.callback_query(F.data == "home:formation")
async def show_formations(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await callback.message.edit_text(
        t(lang, "choose_formation"),
        parse_mode="HTML",
        reply_markup=formation_keyboard(lang),
    )
    await state.set_state(Squad.selecting_formation)
    await callback.answer()


@router.callback_query(F.data.startswith("formation:"), Squad.selecting_formation)
async def set_formation(callback: CallbackQuery, state: FSMContext):
    formation = callback.data.split(":")[1]
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)

    # Load existing squad so we don't wipe already-picked players
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    squad_data["formation"] = formation

    await sheets.update_user(callback.from_user.id, formation=formation)
    await sheets.save_squad(callback.from_user.id, squad_data)
    await _show_squad(callback, user, squad_data, lang, state)


@router.callback_query(F.data == "home:squad")
async def view_squad(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id)
    await _show_squad(callback, user, squad_data, lang, state)


@router.callback_query(F.data == "squad:view")
async def squad_view_direct(callback: CallbackQuery, state: FSMContext):
    await view_squad(callback, state)


@router.callback_query(F.data.startswith("slot:"))
async def show_player_list(callback: CallbackQuery, state: FSMContext):
    _, position, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    await state.update_data(current_slot=slot, current_position=position)

    # If slot already has a player, show Replace / Remove options first
    existing_pid = squad_data.get(slot)
    if existing_pid:
        p = get_player(existing_pid)
        player_name = p["name"] if p else "this player"
        await callback.message.edit_text(
            f"👤 <b>{player_name}</b> is in this slot.\nWhat do you want to do?",
            parse_mode="HTML",
            reply_markup=slot_action_keyboard(lang, position, slot, existing_pid),
        )
        await state.set_state(Squad.selecting_player)
        await callback.answer()
        return

    # For sub slots (ANY), let user pick position first
    if position == "ANY":
        kb = InlineKeyboardBuilder()
        for pos, emoji in [("GK", "🧤"), ("DEF", "🔵"), ("MF", "🟡"), ("FW", "🔴")]:
            kb.button(text=f"{emoji} {pos}", callback_data=f"subpos:{pos}:{slot}")
        kb.button(text=t(lang, "back_home"), callback_data="squad:view")
        kb.adjust(2)
        await callback.message.edit_text(
            "👇 Choose a position for this sub slot:",
            reply_markup=kb.as_markup()
        )
        await state.set_state(Squad.selecting_player)
        await callback.answer()
        return

    all_p = get_by_position(position)
    taken = {v for v in squad_data.values() if isinstance(v, str) and v and not v.startswith("4-")}
    available = [p for p in all_p if p["id"] not in taken]
    total_pages = max(1, -(-len(available) // 8))
    await callback.message.edit_text(
        t(lang, "pick_player", pos=position, page=1, total=total_pages),
        parse_mode="HTML",
        reply_markup=player_list_keyboard(lang, position, slot, 0, squad_data),
    )
    await state.set_state(Squad.selecting_player)
    await callback.answer()


@router.callback_query(F.data.startswith("slot_replace:"))
async def slot_replace(callback: CallbackQuery, state: FSMContext):
    _, position, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    await state.update_data(current_slot=slot, current_position=position)

    # For sub slots (ANY), let user pick position first
    if position == "ANY":
        kb = InlineKeyboardBuilder()
        for pos, emoji in [("GK", "🧤"), ("DEF", "🔵"), ("MF", "🟡"), ("FW", "🔴")]:
            kb.button(text=f"{emoji} {pos}", callback_data=f"subpos:{pos}:{slot}")
        kb.button(text=t(lang, "back_home"), callback_data="squad:view")
        kb.adjust(2)
        await callback.message.edit_text(
            "👇 Choose a position for this sub slot:",
            reply_markup=kb.as_markup()
        )
        await state.set_state(Squad.selecting_player)
        await callback.answer()
        return

    all_p = get_by_position(position)
    taken = {v for v in squad_data.values() if isinstance(v, str) and v and not v.startswith("4-")}
    # Don't exclude the player currently in this slot — they're being replaced
    taken.discard(squad_data.get(slot))
    available = [p for p in all_p if p["id"] not in taken]
    total_pages = max(1, -(-len(available) // 8))
    await callback.message.edit_text(
        t(lang, "pick_player", pos=position, page=1, total=total_pages),
        parse_mode="HTML",
        reply_markup=player_list_keyboard(lang, position, slot, 0, squad_data),
    )
    await state.set_state(Squad.selecting_player)
    await callback.answer()


@router.callback_query(F.data.startswith("slot_remove:"))
async def slot_remove(callback: CallbackQuery, state: FSMContext):
    slot = callback.data.split(":", 1)[1]
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}

    pid = squad_data.get(slot)
    if pid:
        p = get_player(pid)
        budget = _safe_budget(user)
        if p:
            budget += p["price"]  # Refund the player's price
            await sheets.update_user(callback.from_user.id, budget_remaining=budget)
        # Clear captain if the removed player was captain
        if squad_data.get("captain") == pid or (user or {}).get("captain") == pid:
            squad_data["captain"] = ""
            await sheets.update_user(callback.from_user.id, captain="")
        squad_data.pop(slot, None)
        await sheets.save_squad(callback.from_user.id, squad_data)

    fresh_user = await sheets.get_user(callback.from_user.id)
    await _show_squad(callback, fresh_user, squad_data, lang, state)
    try:
        await callback.answer("Player removed." if pid else "Slot already empty.")
    except Exception:
        pass


@router.callback_query(F.data.startswith("subpos:"))
async def select_sub_position(callback: CallbackQuery, state: FSMContext):
    _, position, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    await state.update_data(current_slot=slot, current_position=position)
    all_p = get_by_position(position)
    taken = {v for v in squad_data.values() if isinstance(v, str) and v and not v.startswith("4-")}
    available = [p for p in all_p if p["id"] not in taken]
    total_pages = max(1, -(-len(available) // 8))
    await callback.message.edit_text(
        t(lang, "pick_player", pos=position, page=1, total=total_pages),
        parse_mode="HTML",
        reply_markup=player_list_keyboard(lang, position, slot, 0, squad_data),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("page:"))
async def paginate_players(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    position, slot, page = parts[1], parts[2], int(parts[3])
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    all_p = get_by_position(position)
    taken = {v for v in squad_data.values() if isinstance(v, str) and v and not v.startswith("4-")}
    available = [p for p in all_p if p["id"] not in taken]
    total_pages = max(1, -(-len(available) // 8))
    try:
        await callback.message.edit_text(
            t(lang, "pick_player", pos=position, page=page + 1, total=total_pages),
            parse_mode="HTML",
            reply_markup=player_list_keyboard(lang, position, slot, page, squad_data),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("pick:"))
async def pick_player(callback: CallbackQuery, state: FSMContext):
    _, player_id, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    p = get_player(player_id)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return
    budget = _safe_budget(user)
    if p["price"] > budget:
        await callback.answer(t(lang, "no_budget"), show_alert=True)
        return
    taken = {v for v in squad_data.values() if isinstance(v, str)}
    if player_id in taken:
        await callback.answer(t(lang, "already_in"), show_alert=True)
        return
    remaining = budget - p["price"]
    await callback.message.edit_text(
        t(lang, "confirm_player", name=p["name"], nation=p["nation"], team=p["team"],
          price=fmt_price(p["price"]), remaining=fmt_price(remaining)),
        parse_mode="HTML",
        reply_markup=confirm_player_keyboard(lang, player_id, slot),
    )
    await state.set_state(Squad.confirming_player)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_player:"), Squad.confirming_player)
async def confirm_player(callback: CallbackQuery, state: FSMContext):
    _, player_id, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    p = get_player(player_id)
    if not p:
        await callback.answer("Error.", show_alert=True)
        return
    budget = _safe_budget(user)
    # Refund old player if replacing
    old_pid = squad_data.get(slot)
    if old_pid:
        old_p = get_player(old_pid)
        if old_p:
            budget += old_p["price"]
    budget -= p["price"]
    squad_data[slot] = player_id
    await sheets.save_squad(callback.from_user.id, squad_data)
    await sheets.update_user(callback.from_user.id, budget_remaining=budget)
    # Refresh user cache with new budget
    cached_user = await sheets.get_user(callback.from_user.id)
    await _show_squad(callback, cached_user, squad_data, lang, state)
    # Show toast notification
    try:
        await callback.answer(t(lang, "player_added", name=p["name"]))
    except Exception:
        pass


@router.callback_query(F.data == "squad:captain")
async def choose_captain(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    formation = (user or {}).get("formation", "4-3-3") or "4-3-3"
    await callback.message.edit_text(
        t(lang, "choose_captain"),
        parse_mode="HTML",
        reply_markup=captain_keyboard(lang, squad_data, formation),
    )
    await state.set_state(Squad.selecting_captain)
    await callback.answer()


@router.callback_query(F.data.startswith("captain:"), Squad.selecting_captain)
async def set_captain(callback: CallbackQuery, state: FSMContext):
    player_id = callback.data.split(":")[1]
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    p = get_player(player_id)
    await sheets.update_user(callback.from_user.id, captain=player_id)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    squad_data["captain"] = player_id
    await _show_squad(callback, user, squad_data, lang, state)
    try:
        await callback.answer(t(lang, "captain_set", name=p["name"] if p else ""))
    except Exception:
        pass


@router.callback_query(F.data == "squad:submit")
async def submit_squad_prompt(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    formation = (user or {}).get("formation", "4-3-3") or "4-3-3"
    filled = count_squad_filled(squad_data, formation)
    if filled < 15:
        await callback.answer(t(lang, "squad_incomplete"), show_alert=True)
        return
    captain_id = squad_data.get("captain") or (user or {}).get("captain", "")
    if not captain_id:
        await callback.answer(t(lang, "no_captain"), show_alert=True)
        return
    cap = get_player(captain_id)
    budget_used = config.TOTAL_BUDGET - _safe_budget(user)
    await callback.message.edit_text(
        t(lang, "confirm_submit", formation=formation,
          captain=cap["name"] if cap else "N/A", spent=fmt_price(budget_used)),
        parse_mode="HTML",
        reply_markup=confirm_submit_keyboard(lang),
    )
    await state.set_state(Squad.confirming_submit)
    await callback.answer()


@router.callback_query(F.data == "submit:confirm", Squad.confirming_submit)
async def confirm_submit(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    await sheets.update_user(callback.from_user.id, squad_submitted="yes")
    await callback.message.edit_text(
        t(lang, "squad_submitted"),
        parse_mode="HTML",
        reply_markup=home_keyboard(lang, callback.from_user.id, True, True),
    )
    await state.set_state(Squad.home)
    await callback.answer()


@router.callback_query(F.data == "home:leaderboard")
async def show_leaderboard(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    top = await sheets.get_leaderboard()
    if not top:
        text = t(lang, "leaderboard_empty")
    else:
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        lines = [t(lang, "leaderboard_title")]
        for i, row in enumerate(top):
            lines.append(
                f"{medals[i]} {row.get('rolletto_username', 'N/A')} — "
                f"<b>{row.get('total_points', 0)} pts</b>"
            )
        text = "\n".join(lines)
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()
