"""
squad.py - Squad building with pitch visual and position-based picking.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import sheets
import players as pl_module
from players import get_player, get_players_by_position, fmt_price
from states import Squad
from translations import t
from helpers import (
    get_lang, get_formation_slots, get_starter_slots,
    build_squad_visual, calc_squad_cost,
    squad_is_complete, FORMATIONS
)
from inline import home_keyboard, formation_keyboard, captain_keyboard, squad_review_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()

POS_EMOJI = {"GK": "🧤", "DEF": "🔵", "MF": "🟡", "FW": "🔴"}
POS_NAME  = {"GK": "Goalkeeper", "DEF": "Defender", "MF": "Midfielder", "FW": "Forward"}


def _needs(formation, squad):
    slots_def = get_formation_slots(formation)
    total = {
        "GK":  2,
        "DEF": slots_def["DEF"] + 1,
        "MF":  slots_def["MF"]  + 1,
        "FW":  slots_def["FW"]  + 1,
    }
    for pid in squad.values():
        if isinstance(pid, str) and pid:
            p = get_player(pid)
            if p:
                total[p["position"]] = max(0, total[p["position"]] - 1)
    return total


def _all_filled(formation, squad):
    """Check using same slot names as squad_is_complete in helpers."""
    from helpers import get_all_slots
    slots = get_all_slots(formation)
    return all(squad.get(s) for s in slots)


def _assign_slot(formation, squad, pid, pos):
    """Fill the next empty slot for this position."""
    squad = dict(squad)
    slots_def = get_formation_slots(formation)
    starter_slots = ["gk1"] if pos == "GK" else [pos.lower() + str(i) for i in range(1, slots_def.get(pos, 0) + 1)]
    bench_slot = "bench_" + pos.lower()
    for slot in starter_slots + [bench_slot]:
        if not squad.get(slot):
            squad[slot] = pid
            return squad
    return squad


def _pitch_visual(formation, squad):
    slots_def = get_formation_slots(formation)

    def slot_name(slot):
        pid = squad.get(slot, "")
        if not pid:
            return "[ ? ]"
        p = get_player(pid)
        if not p:
            return "[ ? ]"
        return p["name"].split()[-1][:8]

    def row(names):
        return "  ".join(n.center(9) for n in names)

    lines = []

    # GK
    lines.append(slot_name("gk1").center(40))
    lines.append("")

    # DEF
    def_names = [slot_name("def" + str(i)) for i in range(1, slots_def["DEF"] + 1)]
    lines.append(row(def_names))
    lines.append("")

    # MF
    mf_names = [slot_name("mf" + str(i)) for i in range(1, slots_def["MF"] + 1)]
    lines.append(row(mf_names))
    lines.append("")

    # FW
    fw_names = [slot_name("fw" + str(i)) for i in range(1, slots_def["FW"] + 1)]
    lines.append(row(fw_names))
    lines.append("")

    # Bench
    bench_names = [
        slot_name("bench_gk"),
        slot_name("bench_def"),
        slot_name("bench_mf"),
        slot_name("bench_fw"),
    ]
    lines.append("─── Bench ───")
    lines.append(row(bench_names))

    return "<code>" + "\n".join(lines) + "</code>"


async def _show_position_menu(message, lang, formation, squad, edit=True):
    needs       = _needs(formation, squad)
    budget_used = calc_squad_cost(squad)
    budget_left = config.TOTAL_BUDGET - budget_used
    total_need  = sum(_needs(formation, {}).values())
    picked      = sum(1 for v in squad.values() if isinstance(v, str) and v)

    pitch  = _pitch_visual(formation, squad)
    header = (
        "<b>Build Squad — " + formation + "</b>\n"
        "💰 Budget: " + fmt_price(budget_left) + "  "
        "👥 " + str(picked) + "/" + str(total_need) + "\n\n"
        + pitch + "\n\n"
        "Tap a position to add a player:"
    )

    slots_def = get_formation_slots(formation)

    kb = InlineKeyboardBuilder()

    # GK row
    n_def = slots_def["DEF"]
    n_mf  = slots_def["MF"]
    n_fw  = slots_def["FW"]

    gk_pid = squad.get("gk1", "")
    gk_p   = get_player(gk_pid) if gk_pid else None
    gk_lbl = (gk_p["name"].split()[-1][:10] if gk_p else "GK ?")
    kb.button(text=POS_EMOJI["GK"] + " " + gk_lbl, callback_data="slot_pick:gk1:GK:0")

    # DEF row — one button per slot
    for i in range(1, n_def + 1):
        slot = "def" + str(i)
        pid  = squad.get(slot, "")
        p    = get_player(pid) if pid else None
        lbl  = (p["name"].split()[-1][:8] if p else "DEF ?")
        kb.button(text=POS_EMOJI["DEF"] + " " + lbl, callback_data="slot_pick:" + slot + ":DEF:0")

    # MF row
    for i in range(1, n_mf + 1):
        slot = "mf" + str(i)
        pid  = squad.get(slot, "")
        p    = get_player(pid) if pid else None
        lbl  = (p["name"].split()[-1][:8] if p else "MF ?")
        kb.button(text=POS_EMOJI["MF"] + " " + lbl, callback_data="slot_pick:" + slot + ":MF:0")

    # FW row
    for i in range(1, n_fw + 1):
        slot = "fw" + str(i)
        pid  = squad.get(slot, "")
        p    = get_player(pid) if pid else None
        lbl  = (p["name"].split()[-1][:8] if p else "FW ?")
        kb.button(text=POS_EMOJI["FW"] + " " + lbl, callback_data="slot_pick:" + slot + ":FW:0")

    # Bench row
    for pos in ["GK", "DEF", "MF", "FW"]:
        slot = "bench_" + pos.lower()
        pid  = squad.get(slot, "")
        p    = get_player(pid) if pid else None
        lbl  = (p["name"].split()[-1][:8] if p else pos + " ?")
        kb.button(text=POS_EMOJI[pos] + " " + lbl, callback_data="slot_pick:" + slot + ":" + pos + ":0")

    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1, n_def, n_mf, n_fw, 4, 1)

    try:
        if edit:
            await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
        else:
            await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


async def _show_pos_players(message, lang, formation, squad, pos, page=0, slot=None):
    """Show players for a position. slot = specific slot being replaced (if any)."""
    budget_left = config.TOTAL_BUDGET - calc_squad_cost(squad)

    # Refund the current player in this slot so budget is accurate
    current_pid = squad.get(slot, "") if slot else ""
    current_p   = get_player(current_pid) if current_pid else None
    refund      = current_p["price"] if current_p else 0
    effective_budget = budget_left + refund

    # Exclude all picked players except the one in this slot (can swap with same slot)
    picked_ids = {v for k, v in squad.items() if isinstance(v, str) and v and k != slot}

    available = [
        p for p in get_players_by_position(pos)
        if p["id"] not in picked_ids and p["price"] <= effective_budget
    ]
    available.sort(key=lambda p: -p["price"])

    page_size = 8
    start  = page * page_size
    end    = start + page_size
    page_p = available[start:end]

    replacing = " (replacing)" if current_p else ""
    slot_key  = slot or pos
    header = (
        POS_EMOJI[pos] + " <b>" + POS_NAME[pos] + "s</b>" + replacing + "\n"
        + "💰 Budget: " + fmt_price(effective_budget)
        + (" (+refund)" if refund else "")
    )

    kb = InlineKeyboardBuilder()
    for p in page_p:
        label = p["name"] + " (" + p["team"] + ") — " + fmt_price(p["price"])
        kb.button(text=label, callback_data="slot_pick_confirm:" + slot_key + ":" + pos + ":" + p["id"])

    if page > 0:
        kb.button(text="◀️ Prev", callback_data="slot_pick:" + slot_key + ":" + pos + ":" + str(page - 1))
    if end < len(available):
        kb.button(text="Next ▶️", callback_data="slot_pick:" + slot_key + ":" + pos + ":" + str(page + 1))

    kb.button(text="◀️ Positions", callback_data="squad:positions")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    try:
        await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


# ── Handlers ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:squad")
async def show_squad(callback: CallbackQuery, state: FSMContext):
    uid   = callback.from_user.id
    user  = await sheets.get_user(uid)
    lang  = await get_lang(uid, user)
    squad = await sheets.get_squad(uid)
    formation = (user or {}).get("formation", "4-3-3")

    # Also check FSM state in case not yet saved to DB
    fsm_data = await state.get_data()
    if (not squad or not squad_is_complete(squad, formation)) and fsm_data.get("squad"):
        fsm_squad = fsm_data["squad"]
        fsm_form  = fsm_data.get("formation", formation)
        if _all_filled(fsm_form, fsm_squad):
            squad     = fsm_squad
            formation = fsm_form
            await sheets.save_squad(uid, dict(squad, formation=formation))

    if squad and squad_is_complete(squad, formation):
        captain_id = (user or {}).get("captain", "")
        pts        = await sheets.get_squad_points_summary(uid)
        visual     = build_squad_visual(squad, formation, captain_id, pts)
        confirmed  = (user or {}).get("confirmed", False)
        before_dl  = await sheets.is_before_deadline()

        kb2 = InlineKeyboardBuilder()

        if confirmed:
            # Confirmed — show locked status, only allow Change Team below squad
            if before_dl:
                kb2.button(text="⭐ Change Captain",   callback_data="squad:change_captain")
                kb2.button(text="🔄 Change Team",      callback_data="squad:change_confirmed")
            kb2.button(text=t(lang, "back_home"),      callback_data="home:back")
        else:
            # Not confirmed yet — show confirm + captain + rebuild
            if before_dl:
                kb2.button(text="✅ Confirm Squad",    callback_data="squad:confirm")
                kb2.button(text="⭐ Change Captain",   callback_data="squad:change_captain")
                kb2.button(text="🔄 Rebuild Squad",    callback_data="squad:change")
            kb2.button(text=t(lang, "back_home"),      callback_data="home:back")

        kb2.adjust(1)

        status = "🔒 <b>Confirmed</b>" if confirmed else "⚠️ <b>Not confirmed yet</b>"
        await callback.message.edit_text(
            "📋 <b>My Squad</b>  " + status + "\n\n" + visual,
            parse_mode="HTML",
            reply_markup=kb2.as_markup()
        )
    else:
        await callback.message.edit_text(
            t(lang, "build_squad"), parse_mode="HTML",
            reply_markup=formation_keyboard(lang)
        )
        await state.set_state(Squad.formation)
    await callback.answer()


@router.callback_query(Squad.formation, F.data.startswith("formation:"))
async def pick_formation(callback: CallbackQuery, state: FSMContext):
    uid       = callback.from_user.id
    user      = await sheets.get_user(uid)
    lang      = await get_lang(uid, user)
    formation = callback.data.split(":")[1]

    await state.update_data(formation=formation, squad={})
    await sheets.update_user(uid, formation=formation)
    await _show_position_menu(callback.message, lang, formation, {})
    await state.set_state(Squad.picking_gk)
    await callback.answer()


@router.callback_query(F.data == "squad:positions")
async def back_to_positions(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()
    await _show_position_menu(callback.message, lang,
                               data.get("formation", "4-3-3"),
                               data.get("squad", {}))
    await callback.answer()


@router.callback_query(F.data.startswith("slot_pick:"))
async def slot_pick_cb(callback: CallbackQuery, state: FSMContext):
    """Show player list for a specific slot. Format: slot_pick:SLOT:POS:PAGE"""
    parts = callback.data.split(":")
    slot, pos, page = parts[1], parts[2], int(parts[3])
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()
    squad = data.get("squad", {})

    # If squad not in state, load from DB
    if not squad:
        db_squad = await sheets.get_squad(uid)
        if db_squad:
            squad = db_squad
            formation = (user or {}).get("formation", "4-3-3")
            await state.update_data(squad=squad, formation=formation)

    await _show_pos_players(callback.message, lang,
                             data.get("formation", (user or {}).get("formation", "4-3-3")),
                             squad, pos, page, slot=slot)
    await callback.answer()


@router.callback_query(F.data.startswith("slot_pick_confirm:"))
async def slot_pick_confirm(callback: CallbackQuery, state: FSMContext):
    """User picked a player for a specific slot. Format: slot_pick_confirm:SLOT:POS:PID"""
    parts     = callback.data.split(":")
    slot, pos, pid = parts[1], parts[2], parts[3]
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    squad     = dict(data.get("squad", {}))

    # Load from DB if state is empty
    if not squad:
        db_squad = await sheets.get_squad(uid)
        if db_squad:
            squad = db_squad

    p = get_player(pid)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return

    # Budget check — refund current slot player
    current_pid = squad.get(slot, "")
    current_p   = get_player(current_pid) if current_pid else None
    refund      = current_p["price"] if current_p else 0
    new_cost    = calc_squad_cost(squad) - refund + p["price"]

    if new_cost > config.TOTAL_BUDGET:
        await callback.answer(t(lang, "over_budget"), show_alert=True)
        return

    # Place player in exact slot
    squad[slot] = pid
    await state.update_data(squad=squad)

    if _all_filled(formation, squad):
        await sheets.save_squad(uid, dict(squad, formation=formation))
        await _show_captain_picker(callback.message, lang, squad, formation)
        await state.set_state(Squad.captain)
    else:
        await _show_position_menu(callback.message, lang, formation, squad)

    await callback.answer()


async def _show_captain_picker(message, lang, squad, formation):
    kb = captain_keyboard(squad, formation, lang)
    txt = (
        "⭐ <b>Choose your captain</b>\n\n"
        "Captain scores ×2 points.\n"
        "You cannot confirm without a captain."
    )
    try:
        await message.edit_text(txt, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await message.answer(txt, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "squad:change_confirmed")
async def change_confirmed_squad(callback: CallbackQuery, state: FSMContext):
    """Change team after confirmation — show formation picker."""
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    await callback.message.edit_text(
        "🔄 <b>Change Team</b>\n\nChoose your new formation:",
        parse_mode="HTML",
        reply_markup=formation_keyboard(lang)
    )
    # Reset confirmation so they must re-confirm after changing
    await sheets.update_user(uid, confirmed=False)
    await state.set_state(Squad.formation)
    await callback.answer()


@router.callback_query(F.data == "squad:change_captain")
async def change_captain(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    squad     = await sheets.get_squad(uid)
    formation = (user or {}).get("formation", "4-3-3")
    if not squad:
        await callback.answer("No squad found.", show_alert=True)
        return

    await state.update_data(squad=squad, formation=formation)
    await _show_captain_picker(callback.message, lang, squad, formation)
    await state.set_state(Squad.captain)
    await callback.answer()


@router.callback_query(Squad.captain, F.data.startswith("captain:"))
async def pick_captain(callback: CallbackQuery, state: FSMContext):
    pid  = callback.data.split(":")[1]
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    squad     = data.get("squad", {})
    formation = data.get("formation", "4-3-3")
    p         = get_player(pid)

    await sheets.update_user(uid, captain=pid)
    await sheets.save_squad(uid, dict(squad, formation=formation))

    visual = build_squad_visual(squad, formation, pid)
    cap_name = p["name"] if p else pid
    await callback.message.edit_text(
        "⭐ Captain: <b>" + cap_name + "</b>\n\n📋 <b>Squad Review</b>\n\n" + visual,
        parse_mode="HTML",
        reply_markup=squad_review_keyboard(lang, confirmed=False)
    )
    await state.set_state(Squad.review)
    await callback.answer()


@router.callback_query(F.data == "squad:confirm")
async def confirm_squad(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    if not user.get("captain"):
        await callback.answer(t(lang, "no_captain"), show_alert=True)
        return
    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    squad     = await sheets.get_squad(uid)
    formation = user.get("formation", "4-3-3")

    # Also check FSM state in case squad not fully saved yet
    fsm_data  = await state.get_data()
    if fsm_data.get("squad") and _all_filled(fsm_data.get("formation", formation), fsm_data["squad"]):
        squad     = fsm_data["squad"]
        formation = fsm_data.get("formation", formation)
        await sheets.save_squad(uid, dict(squad, formation=formation))

    if not squad or not squad_is_complete(squad, formation):
        await callback.answer(t(lang, "no_squad"), show_alert=True)
        return

    gw = await sheets.get_active_gameweek()
    if not gw:
        await callback.answer("No active gameweek. Admin needs to run /fixtures first.", show_alert=True)
        return

    await sheets.confirm_squad(uid, gw["id"], squad)
    import config as _config
    await callback.message.edit_text(
        t(lang, "squad_confirmed"), parse_mode="HTML",
        reply_markup=home_keyboard(lang, is_admin=uid == _config.ADMIN_ID)
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "squad:change")
async def change_squad(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    await callback.message.edit_text(
        t(lang, "build_squad"), parse_mode="HTML",
        reply_markup=formation_keyboard(lang)
    )
    await state.set_state(Squad.formation)
    await callback.answer()


@router.callback_query(F.data == "home:confirm")
async def home_confirm(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    if user.get("confirmed"):
        await callback.answer(t(lang, "already_confirmed"), show_alert=True)
        return
    if not user.get("captain"):
        await callback.answer(t(lang, "no_captain"), show_alert=True)
        return
    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    squad     = await sheets.get_squad(uid)
    formation = user.get("formation", "4-3-3")
    if not squad or not squad_is_complete(squad, formation):
        await callback.answer(t(lang, "no_squad"), show_alert=True)
        return

    gw = await sheets.get_active_gameweek()
    if not gw:
        await callback.answer("No active gameweek.", show_alert=True)
        return

    await sheets.confirm_squad(uid, gw["id"], squad)
    import config as _config
    await callback.message.edit_text(
        t(lang, "squad_confirmed"), parse_mode="HTML",
        reply_markup=home_keyboard(lang, is_admin=uid == _config.ADMIN_ID)
    )
    await callback.answer()
