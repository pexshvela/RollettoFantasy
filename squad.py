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
    raw = (user or {}).get("budget_remaining", config.TOTAL_BUDGET)
    try:
        return int(float(raw or config.TOTAL_BUDGET))
    except (ValueError, TypeError):
        return config.TOTAL_BUDGET


def _merge_captain(user, squad_data):
    """Inject captain from user record into squad_data for display only — never saved."""
    if squad_data is None:
        squad_data = {}
    captain = (user or {}).get("captain", "")
    if captain:
        squad_data = dict(squad_data)  # copy so we don't pollute the original
        squad_data["captain"] = captain
    return squad_data


async def _show_squad(callback, user, squad_data, lang, state):
    """Central render helper for squad view."""
    formation = (user or {}).get("formation", "4-3-3") or "4-3-3"
    budget = _safe_budget(user)
    display_squad = _merge_captain(user, squad_data or {})
    visual = build_squad_visual(formation, display_squad)
    text = t(lang, "squad_view", formation=formation,
             budget=fmt_price(budget), visual=visual)
    if len(text) > 4000:
        text = text[:4000] + "…"
    try:
        await callback.message.edit_text(
            text, parse_mode="HTML",
            reply_markup=squad_keyboard(lang, formation, display_squad),
        )
    except TelegramBadRequest as e:
        err = str(e)
        if "message is not modified" in err:
            pass
        elif "MESSAGE_TOO_LONG" in err:
            fallback = t(lang, "squad_view", formation=formation,
                         budget=fmt_price(budget), visual="[tap a slot to see]")
            await callback.message.edit_text(
                fallback, parse_mode="HTML",
                reply_markup=squad_keyboard(lang, formation, display_squad),
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
        t(lang, "choose_formation"), parse_mode="HTML",
        reply_markup=formation_keyboard(lang),
    )
    await state.set_state(Squad.selecting_formation)
    await callback.answer()


@router.callback_query(F.data.startswith("formation:"), Squad.selecting_formation)
async def set_formation(callback: CallbackQuery, state: FSMContext):
    formation = callback.data.split(":")[1]
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    squad_data["formation"] = formation
    await sheets.update_user(callback.from_user.id, formation=formation)
    await sheets.save_squad(callback.from_user.id, squad_data)
    user = await sheets.get_user(callback.from_user.id)
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
async def tap_slot(callback: CallbackQuery, state: FSMContext):
    _, position, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    existing_pid = squad_data.get(slot)

    if existing_pid:
        # Slot filled → show Replace / Remove menu
        p = get_player(existing_pid)
        name = p["name"] if p else "this player"
        await callback.message.edit_text(
            f"👤 <b>{name}</b>\n\nWhat do you want to do?",
            parse_mode="HTML",
            reply_markup=slot_action_keyboard(lang, position, slot, existing_pid),
        )
        await state.update_data(current_slot=slot, current_position=position)
        await state.set_state(Squad.selecting_player)
        await callback.answer()
        return

    # Slot empty
    await _open_player_list(callback, state, position, slot, squad_data, lang)


@router.callback_query(F.data.startswith("slot_replace:"))
async def slot_replace(callback: CallbackQuery, state: FSMContext):
    _, position, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    await state.update_data(current_slot=slot, current_position=position,
                            replacing_pid=squad_data.get(slot))
    await _open_player_list(callback, state, position, slot, squad_data, lang,
                            exclude_current=True)


@router.callback_query(F.data.startswith("slot_remove:"))
async def slot_remove(callback: CallbackQuery, state: FSMContext):
    """Remove player from slot, refund budget, update DB and cache properly."""
    slot = callback.data.split(":", 1)[1]
    uid = callback.from_user.id

    # Always fetch fresh squad from cache/DB
    squad_data = await sheets.get_squad(uid) or {}
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    pid = squad_data.get(slot)
    if not pid:
        # Already empty — just re-render
        await _show_squad(callback, user, squad_data, lang, state)
        return

    p = get_player(pid)
    budget = _safe_budget(user)
    if p:
        budget += p["price"]

    # CRITICAL: set to "" (not pop) so Supabase clears the column
    squad_data[slot] = ""

    # Clear captain if this player was captain
    captain = (user or {}).get("captain", "")
    if captain == pid:
        await sheets.update_user(uid, captain="", budget_remaining=budget)
    else:
        await sheets.update_user(uid, budget_remaining=budget)

    await sheets.save_squad(uid, squad_data)

    # Get refreshed user (budget updated in cache by update_user)
    user = await sheets.get_user(uid)
    # Remove the now-empty key for clean display
    display_squad = {k: v for k, v in squad_data.items() if v}

    await _show_squad(callback, user, display_squad, lang, state)


async def _open_player_list(callback, state, position, slot, squad_data, lang,
                             exclude_current=False):
    """Show player selection list, optionally including the current slot's player."""
    if position == "ANY":
        kb = InlineKeyboardBuilder()
        for pos, emoji in [("GK", "🧤"), ("DEF", "🔵"), ("MF", "🟡"), ("FW", "🔴")]:
            kb.button(text=f"{emoji} {pos}", callback_data=f"subpos:{pos}:{slot}")
        kb.button(text="◀️ Back", callback_data="squad:view")
        kb.adjust(2)
        await callback.message.edit_text(
            "👇 Choose position for this sub:", reply_markup=kb.as_markup()
        )
        await state.set_state(Squad.selecting_player)
        await callback.answer()
        return

    all_p = get_by_position(position)
    # Build taken set — exclude formation strings and empty values
    taken = {v for v in squad_data.values()
             if isinstance(v, str) and v and not _is_formation(v)}
    if exclude_current:
        taken.discard(squad_data.get(slot))  # allow replacing with same player
    available = [p for p in all_p if p["id"] not in taken]
    total_pages = max(1, -(-len(available) // 8))

    await callback.message.edit_text(
        t(lang, "pick_player", pos=position, page=1, total=total_pages),
        parse_mode="HTML",
        reply_markup=player_list_keyboard(lang, position, slot, 0, squad_data),
    )
    await state.set_state(Squad.selecting_player)
    await callback.answer()


def _is_formation(val: str) -> bool:
    """Check if a string looks like a formation (e.g. '4-3-3')."""
    return bool(val and val.count("-") == 2 and all(c.isdigit() or c == "-" for c in val))


@router.callback_query(F.data.startswith("subpos:"))
async def select_sub_position(callback: CallbackQuery, state: FSMContext):
    _, position, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    await state.update_data(current_slot=slot, current_position=position)
    await _open_player_list(callback, state, position, slot, squad_data, lang)


@router.callback_query(F.data.startswith("page:"))
async def paginate_players(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    position, slot, page = parts[1], parts[2], int(parts[3])
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    all_p = get_by_position(position)
    taken = {v for v in squad_data.values()
             if isinstance(v, str) and v and not _is_formation(v)}
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
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    squad_data = await sheets.get_squad(uid) or {}
    p = get_player(player_id)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return

    budget = _safe_budget(user)
    old_pid = squad_data.get(slot)
    # Calculate effective budget (refund old player if replacing)
    effective_budget = budget
    if old_pid and old_pid != player_id:
        old_p = get_player(old_pid)
        if old_p:
            effective_budget += old_p["price"]

    if p["price"] > effective_budget:
        await callback.answer(t(lang, "no_budget"), show_alert=True)
        return

    # Check not already picked in a different slot
    taken = {v for v in squad_data.values() if isinstance(v, str) and v and not _is_formation(v)}
    taken.discard(old_pid)  # allow picking same player as replacement
    if player_id in taken:
        await callback.answer(t(lang, "already_in"), show_alert=True)
        return

    remaining = effective_budget - p["price"]
    old_p = get_player(old_pid) if old_pid else None
    swap_note = f"\n\n🔄 <i>Replacing: {old_p['name']}</i>" if old_p else ""

    await callback.message.edit_text(
        t(lang, "confirm_player", name=p["name"], nation=p["nation"], team=p["team"],
          price=fmt_price(p["price"]), remaining=fmt_price(remaining)) + swap_note,
        parse_mode="HTML",
        reply_markup=confirm_player_keyboard(lang, player_id, slot),
    )
    await state.set_state(Squad.confirming_player)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_player:"), Squad.confirming_player)
async def confirm_player(callback: CallbackQuery, state: FSMContext):
    _, player_id, slot = callback.data.split(":", 2)
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    # Re-fetch squad to avoid stale data
    squad_data = await sheets.get_squad(uid) or {}
    p = get_player(player_id)
    if not p:
        await callback.answer("Error.", show_alert=True)
        return

    budget = _safe_budget(user)
    old_pid = squad_data.get(slot)
    if old_pid:
        old_p = get_player(old_pid)
        if old_p:
            budget += old_p["price"]
        # If old player was captain, clear captain
        if (user or {}).get("captain") == old_pid:
            await sheets.update_user(uid, captain="")

    budget -= p["price"]
    squad_data[slot] = player_id

    await sheets.save_squad(uid, squad_data)
    await sheets.update_user(uid, budget_remaining=budget)

    user = await sheets.get_user(uid)
    await _show_squad(callback, user, squad_data, lang, state)
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

    # Check squad is full before allowing captain selection
    filled = count_squad_filled(squad_data, formation)
    if filled < 15:
        await callback.answer(t(lang, "squad_incomplete"), show_alert=True)
        return

    await callback.message.edit_text(
        t(lang, "choose_captain"), parse_mode="HTML",
        reply_markup=captain_keyboard(lang, squad_data, formation),
    )
    await state.set_state(Squad.selecting_captain)
    await callback.answer()


@router.callback_query(F.data.startswith("captain:"), Squad.selecting_captain)
async def set_captain(callback: CallbackQuery, state: FSMContext):
    player_id = callback.data.split(":")[1]
    uid = callback.from_user.id
    p = get_player(player_id)
    await sheets.update_user(uid, captain=player_id)
    # Get fresh user so captain shows correctly
    user = await sheets.get_user(uid)
    squad_data = await sheets.get_squad(uid) or {}
    await _show_squad(callback, user, squad_data, lang := await get_lang(uid, user), state)
    try:
        await callback.answer(t(lang, "captain_set", name=p["name"] if p else ""))
    except Exception:
        pass


@router.callback_query(F.data == "squad:submit")
async def submit_squad_prompt(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    squad_data = await sheets.get_squad(uid) or {}
    formation = (user or {}).get("formation", "4-3-3") or "4-3-3"
    filled = count_squad_filled(squad_data, formation)
    if filled < 15:
        await callback.answer(t(lang, "squad_incomplete"), show_alert=True)
        return
    captain_id = (user or {}).get("captain", "")
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
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    await sheets.update_user(uid, squad_submitted="yes")
    await callback.message.edit_text(
        t(lang, "squad_submitted"), parse_mode="HTML",
        reply_markup=home_keyboard(lang, uid, True, True),
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
