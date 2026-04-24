"""
squad.py — Squad building, captain selection, confirmation.
Formation → pick GK → pick DEFs → pick MFs → pick FWs → pick bench → captain → confirm
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import sheets
import players as pl_module
from players import get_player, get_players_by_position, fmt_price
from states import Squad
from translations import t
from helpers import (
    get_lang, get_formation_slots, get_starter_slots,
    get_bench_slots, get_all_slots, slot_to_position,
    build_squad_visual, calc_squad_cost, squad_is_complete, FORMATIONS
)
from inline import (
    home_keyboard, formation_keyboard, player_list_keyboard,
    captain_keyboard, squad_review_keyboard, back_home
)
import config

logger = logging.getLogger(__name__)
router = Router()

POS_ORDER  = ["GK", "DEF", "MF", "FW"]
BENCH_POSITIONS = ["GK", "DEF", "MF", "FW"]


# ── Entry point ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:squad")
async def show_squad(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    squad = await sheets.get_squad(uid)

    if squad and squad_is_complete(squad, user.get("formation", "4-3-3")):
        # Show existing squad
        formation  = user.get("formation", "4-3-3")
        captain_id = user.get("captain", "")
        pts        = await sheets.get_squad_points_summary(uid)
        visual     = build_squad_visual(squad, formation, captain_id, pts)
        await callback.message.edit_text(
            f"📋 <b>My Squad</b>\n\n{visual}",
            parse_mode="HTML",
            reply_markup=squad_review_keyboard(lang, confirmed=user.get("confirmed", False))
        )
    else:
        # Build new squad
        await callback.message.edit_text(
            t(lang, "build_squad"),
            parse_mode="HTML",
            reply_markup=formation_keyboard(lang)
        )
        await state.set_state(Squad.formation)

    await callback.answer()


# ── Formation selection ───────────────────────────────────────────────────────

@router.callback_query(Squad.formation, F.data.startswith("formation:"))
async def pick_formation(callback: CallbackQuery, state: FSMContext):
    uid       = callback.from_user.id
    user      = await sheets.get_user(uid)
    lang      = await get_lang(uid, user)
    formation = callback.data.split(":")[1]

    await state.update_data(
        formation=formation,
        squad={},
        picking_pos="GK",
        picking_index=1,
        bench_index=0,
    )
    await sheets.update_user(uid, formation=formation)

    await _show_player_picker(callback.message, lang, formation, "GK", 1, {}, state)
    await state.set_state(Squad.picking_gk)
    await callback.answer()


# ── Player picking ────────────────────────────────────────────────────────────

async def _show_player_picker(message, lang: str, formation: str,
                               pos: str, slot_num: int,
                               current_squad: dict, state: FSMContext, page: int = 0):
    all_p = get_players_by_position(pos)
    budget_used = calc_squad_cost(current_squad)
    budget_left = config.TOTAL_BUDGET - budget_used

    # Filter by budget
    affordable = [p for p in all_p if p["price"] <= budget_left
                  and p["id"] not in current_squad.values()]

    slots_def = get_formation_slots(formation)
    total_in_pos = 1 if pos == "GK" else slots_def.get(pos, 1)

    title = (f"🔢 Slot {slot_num}/{total_in_pos} — {pos}\n"
             f"💰 Budget left: {fmt_price(budget_left)}\n"
             f"Pick your <b>{pos}</b>:")

    kb = player_list_keyboard(affordable, pos, lang, page)
    try:
        await message.edit_text(title, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await message.answer(title, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("page:"))
async def paginate_players(callback: CallbackQuery, state: FSMContext):
    _, pos, page_str = callback.data.split(":")
    page = int(page_str)
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    squad     = data.get("squad", {})
    formation = data.get("formation", "4-3-3")
    slot_num  = data.get("picking_index", 1)

    await _show_player_picker(callback.message, lang, formation, pos, slot_num, squad, state, page)
    await callback.answer()


@router.callback_query(F.data.startswith("pick:"))
async def pick_player(callback: CallbackQuery, state: FSMContext):
    _, pos, pid = callback.data.split(":")
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    squad     = data.get("squad", {}).copy()
    formation = data.get("formation", "4-3-3")
    slots_def = get_formation_slots(formation)

    # Determine current slot name
    bench_idx = data.get("bench_index", 0)
    is_bench  = data.get("picking_bench", False)

    if is_bench:
        bench_positions = BENCH_POSITIONS
        bench_pos = bench_positions[bench_idx]
        slot_name = f"bench_{bench_pos.lower()}"
        squad[slot_name] = pid
        bench_idx += 1

        if bench_idx < len(bench_positions):
            await state.update_data(squad=squad, bench_index=bench_idx)
            next_pos = bench_positions[bench_idx]
            await _show_player_picker(callback.message, lang, formation, next_pos, bench_idx + 1, squad, state)
        else:
            # All bench filled → pick captain
            await state.update_data(squad=squad)
            await _show_captain_picker(callback.message, lang, squad, formation)
            await state.set_state(Squad.captain)
    else:
        # Starter picking
        idx = data.get("picking_index", 1)
        if pos == "GK":
            slot_name = "gk1"
        else:
            slot_name = f"{pos.lower()}{idx}"

        squad[slot_name] = pid
        idx += 1

        # Determine next position
        total_in_pos = slots_def.get(pos, 1)
        if pos == "GK":
            total_in_pos = 1

        if idx <= total_in_pos:
            await state.update_data(squad=squad, picking_index=idx)
            await _show_player_picker(callback.message, lang, formation, pos, idx, squad, state)
        else:
            # Move to next position
            pos_order = ["GK", "DEF", "MF", "FW"]
            current_idx = pos_order.index(pos)
            next_positions = [p for p in pos_order[current_idx + 1:]
                              if slots_def.get(p, 0 if p != "GK" else 1) > 0]

            if next_positions:
                next_pos = next_positions[0]
                await state.update_data(squad=squad, picking_pos=next_pos, picking_index=1)
                await _show_player_picker(callback.message, lang, formation, next_pos, 1, squad, state)
                # Update FSM state
                state_map = {"DEF": Squad.picking_def, "MF": Squad.picking_mf, "FW": Squad.picking_fw}
                await state.set_state(state_map.get(next_pos, Squad.picking_fw))
            else:
                # All starters picked — now bench
                await state.update_data(squad=squad, picking_bench=True, bench_index=0)
                first_bench_pos = BENCH_POSITIONS[0]
                await _show_player_picker(callback.message, lang, formation, first_bench_pos, 1, squad, state)
                await state.set_state(Squad.picking_bench)

    await callback.answer()


# Register pick handler for all squad states
for _state in [Squad.picking_gk, Squad.picking_def, Squad.picking_mf,
               Squad.picking_fw, Squad.picking_bench]:
    router.callback_query.register(pick_player, F.data.startswith("pick:"), _state)


# ── Captain selection ─────────────────────────────────────────────────────────

async def _show_captain_picker(message, lang: str, squad: dict, formation: str):
    kb = captain_keyboard(squad, formation, lang)
    try:
        await message.edit_text(t(lang, "pick_captain"), parse_mode="HTML", reply_markup=kb)
    except Exception:
        await message.answer(t(lang, "pick_captain"), parse_mode="HTML", reply_markup=kb)


@router.callback_query(Squad.captain, F.data.startswith("captain:"))
async def pick_captain(callback: CallbackQuery, state: FSMContext):
    pid  = callback.data.split(":")[1]
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    squad     = data.get("squad", {})
    formation = data.get("formation", "4-3-3")
    p = get_player(pid)

    await sheets.update_user(uid, captain=pid)
    await sheets.save_squad(uid, {**squad, "formation": formation})

    visual = build_squad_visual(squad, formation, pid)
    kb = squad_review_keyboard(lang, confirmed=False)

    await callback.message.edit_text(
        f"✅ Captain set: <b>{p['name'] if p else pid}</b>\n\n📋 <b>Squad Review</b>\n\n{visual}",
        parse_mode="HTML",
        reply_markup=kb
    )
    await state.set_state(Squad.review)
    await callback.answer()


# ── Squad confirm ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "squad:confirm")
async def confirm_squad(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    # Check captain
    captain = user.get("captain", "")
    if not captain:
        await callback.answer(t(lang, "no_captain"), show_alert=True)
        return

    # Check deadline
    before_deadline = await sheets.is_before_deadline()
    if not before_deadline:
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    # Check squad complete
    squad = await sheets.get_squad(uid)
    formation = user.get("formation", "4-3-3")
    if not squad or not squad_is_complete(squad, formation):
        await callback.answer(t(lang, "no_squad"), show_alert=True)
        return

    # Get active gameweek
    gw = await sheets.get_active_gameweek()
    if not gw:
        await callback.answer("No active gameweek. Admin needs to set up fixtures first.", show_alert=True)
        return

    # Save confirmation with squad snapshot
    await sheets.confirm_squad(uid, gw["id"], squad)

    await callback.message.edit_text(
        t(lang, "squad_confirmed"),
        parse_mode="HTML",
        reply_markup=home_keyboard(lang)
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "squad:change")
async def change_player(callback: CallbackQuery, state: FSMContext):
    """Go back to formation selection to rebuild squad."""
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    await callback.message.edit_text(
        t(lang, "build_squad"),
        parse_mode="HTML",
        reply_markup=formation_keyboard(lang)
    )
    await state.set_state(Squad.formation)
    await callback.answer()


@router.callback_query(F.data == "home:confirm")
async def home_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm button from home — shortcut."""
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    if user.get("confirmed"):
        await callback.answer(t(lang, "already_confirmed"), show_alert=True)
        return

    squad = await sheets.get_squad(uid)
    formation = user.get("formation", "4-3-3")

    if not squad or not squad_is_complete(squad, formation):
        await callback.answer(t(lang, "no_squad"), show_alert=True)
        return

    if not user.get("captain"):
        await callback.answer(t(lang, "no_captain"), show_alert=True)
        return

    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    gw = await sheets.get_active_gameweek()
    if not gw:
        await callback.answer("No active gameweek.", show_alert=True)
        return

    await sheets.confirm_squad(uid, gw["id"], squad)
    await callback.message.edit_text(
        t(lang, "squad_confirmed"),
        parse_mode="HTML",
        reply_markup=home_keyboard(lang)
    )
    await callback.answer()
