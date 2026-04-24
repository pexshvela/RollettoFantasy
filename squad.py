"""
squad.py — Sequential squad building:
Formation → pick GK → pick DEFs one by one → pick MFs → pick FWs → pick bench (GK/DEF/MF/FW)
Pitch visual shown at top throughout.
After all 15 picked → captain → review → confirm.
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
    build_squad_visual, calc_squad_cost, squad_is_complete, FORMATIONS
)
from inline import home_keyboard, formation_keyboard, captain_keyboard, squad_review_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()

POS_EMOJI = {"GK": "🧤", "DEF": "🔵", "MF": "🟡", "FW": "🔴"}
POS_NAME  = {"GK": "Goalkeeper", "DEF": "Defender", "MF": "Midfielder", "FW": "Forward"}


# ── Picking order ─────────────────────────────────────────────────────────────

def _pick_order(formation: str) -> list[str]:
    """Return ordered list of slots to fill: starters then bench."""
    slots_def = get_formation_slots(formation)
    order = ["gk1"]
    for i in range(1, slots_def["DEF"] + 1): order.append(f"def{i}")
    for i in range(1, slots_def["MF"]  + 1): order.append(f"mf{i}")
    for i in range(1, slots_def["FW"]  + 1): order.append(f"fw{i}")
    order += ["bench_gk", "bench_def", "bench_mf", "bench_fw"]
    return order


def _slot_pos(slot: str) -> str:
    if slot.startswith("gk") or slot == "bench_gk":   return "GK"
    if slot.startswith("def") or slot == "bench_def":  return "DEF"
    if slot.startswith("mf") or slot == "bench_mf":    return "MF"
    if slot.startswith("fw") or slot == "bench_fw":    return "FW"
    return "FW"


def _next_slot(formation: str, squad: dict) -> str | None:
    """Return the next unfilled slot in picking order, or None if complete."""
    for slot in _pick_order(formation):
        if not squad.get(slot):
            return slot
    return None


def _pitch_visual(formation: str, squad: dict) -> str:
    slots_def = get_formation_slots(formation)

    def name_in_slot(slot):
        pid = squad.get(slot, "")
        if not pid: return "[ ? ]"
        p = get_player(pid)
        return p["name"].split()[-1][:9] if p else "[ ? ]"

    def row(names):
        return "  ".join(n.center(9) for n in names)

    lines = [
        name_in_slot("gk1").center(40),
        "",
        row([name_in_slot(f"def{i}") for i in range(1, slots_def["DEF"] + 1)]),
        "",
        row([name_in_slot(f"mf{i}") for i in range(1, slots_def["MF"] + 1)]),
        "",
        row([name_in_slot(f"fw{i}") for i in range(1, slots_def["FW"] + 1)]),
        "",
        "\u2500\u2500\u2500 Bench \u2500\u2500\u2500",
        row([name_in_slot("bench_gk"), name_in_slot("bench_def"),
             name_in_slot("bench_mf"), name_in_slot("bench_fw")]),
    ]
    return "<code>" + "\n".join(lines) + "</code>"


# ── Show player picker for a slot ─────────────────────────────────────────────

async def _show_picker(message, lang: str, formation: str, squad: dict,
                        slot: str, page: int = 0):
    pos         = _slot_pos(slot)
    picked_ids  = {v for v in squad.values() if isinstance(v, str) and v}
    budget_used = calc_squad_cost(squad)
    budget_left = config.TOTAL_BUDGET - budget_used

    is_bench = slot.startswith("bench_")
    label    = ("Bench " if is_bench else "") + POS_NAME[pos]

    available = [
        p for p in get_players_by_position(pos)
        if p["id"] not in picked_ids and p["price"] <= budget_left
    ]
    available.sort(key=lambda p: -p["price"])

    pitch  = _pitch_visual(formation, squad)
    filled = sum(1 for v in squad.values() if isinstance(v, str) and v)
    total  = len(_pick_order(formation))

    header = (
        "<b>" + formation + "</b>  💰 " + fmt_price(budget_left)
        + "  👥 " + str(filled) + "/" + str(total) + "\n\n"
        + pitch + "\n\n"
        + POS_EMOJI[pos] + " Pick your <b>" + label + "</b>:"
    )

    page_size = 8
    start = page * page_size
    end   = start + page_size
    page_p = available[start:end]

    kb = InlineKeyboardBuilder()
    for p in page_p:
        label_btn = p["name"] + " (" + p["team"] + ") — " + fmt_price(p["price"])
        kb.button(text=label_btn, callback_data="spick:" + slot + ":" + p["id"])

    if page > 0:
        kb.button(text="◀️ Prev", callback_data="spage:" + slot + ":" + str(page - 1))
    if end < len(available):
        kb.button(text="Next ▶️", callback_data="spage:" + slot + ":" + str(page + 1))

    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    try:
        await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


# ── Entry point ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:squad")
async def show_squad(callback: CallbackQuery, state: FSMContext):
    uid   = callback.from_user.id
    user  = await sheets.get_user(uid)
    lang  = await get_lang(uid, user)
    squad = await sheets.get_squad(uid)
    formation = (user or {}).get("formation", "4-3-3")

    if squad and squad_is_complete(squad, formation):
        captain_id = (user or {}).get("captain", "")
        confirmed  = (user or {}).get("confirmed", False)
        pts        = await sheets.get_squad_points_summary(uid)
        visual     = build_squad_visual(squad, formation, captain_id, pts)
        before_dl  = await sheets.is_before_deadline()

        kb = InlineKeyboardBuilder()
        if confirmed:
            if before_dl:
                kb.button(text="⭐ Change Captain", callback_data="squad:change_captain")
                kb.button(text="🔄 Change Team",    callback_data="squad:change_confirmed")
        else:
            if before_dl:
                kb.button(text="✅ Confirm Squad",  callback_data="squad:confirm")
                kb.button(text="⭐ Change Captain", callback_data="squad:change_captain")
                kb.button(text="🔄 Rebuild Squad",  callback_data="squad:change")
        kb.button(text=t(lang, "back_home"), callback_data="home:back")
        kb.adjust(1)

        status = "🔒 <b>Confirmed</b>" if confirmed else "⚠️ <b>Not confirmed</b>"
        await callback.message.edit_text(
            "📋 <b>My Squad</b>  " + status + "\n\n" + visual,
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )
    else:
        await callback.message.edit_text(
            t(lang, "build_squad"), parse_mode="HTML",
            reply_markup=formation_keyboard(lang)
        )
        await state.set_state(Squad.formation)
    await callback.answer()


# ── Formation ─────────────────────────────────────────────────────────────────

@router.callback_query(Squad.formation, F.data.startswith("formation:"))
async def pick_formation(callback: CallbackQuery, state: FSMContext):
    uid       = callback.from_user.id
    user      = await sheets.get_user(uid)
    lang      = await get_lang(uid, user)
    formation = callback.data.split(":")[1]

    squad = {}
    await state.update_data(formation=formation, squad=squad)
    await sheets.update_user(uid, formation=formation)

    first_slot = _next_slot(formation, squad)
    await _show_picker(callback.message, lang, formation, squad, first_slot)
    await state.set_state(Squad.picking_gk)
    await callback.answer()


# ── Pagination ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("spage:"))
async def paginate(callback: CallbackQuery, state: FSMContext):
    _, slot, page_str = callback.data.split(":")
    page = int(page_str)
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()
    await _show_picker(callback.message, lang,
                        data.get("formation", "4-3-3"),
                        data.get("squad", {}), slot, page)
    await callback.answer()


# ── Pick player ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("spick:"))
async def pick_player(callback: CallbackQuery, state: FSMContext):
    parts     = callback.data.split(":")
    slot, pid = parts[1], parts[2]
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    formation = data.get("formation", "4-3-3")
    squad     = dict(data.get("squad", {}))

    p = get_player(pid)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return

    budget_left = config.TOTAL_BUDGET - calc_squad_cost(squad)
    if p["price"] > budget_left:
        await callback.answer(t(lang, "over_budget"), show_alert=True)
        return

    squad[slot] = pid
    await state.update_data(squad=squad)

    next_slot = _next_slot(formation, squad)

    if next_slot is None:
        # All filled — save and go to captain
        await sheets.save_squad(uid, dict(squad, formation=formation))
        await _show_captain_picker(callback.message, lang, squad, formation)
        await state.set_state(Squad.captain)
    else:
        await _show_picker(callback.message, lang, formation, squad, next_slot)

    await callback.answer()


# ── Captain ───────────────────────────────────────────────────────────────────

async def _show_captain_picker(message, lang, squad, formation):
    kb = captain_keyboard(squad, formation, lang)
    try:
        await message.edit_text(
            "⭐ <b>Choose your captain</b>\n\nCaptain scores ×2 points.\nNo captain = cannot confirm.",
            parse_mode="HTML", reply_markup=kb
        )
    except Exception:
        await message.answer(
            "⭐ <b>Choose your captain</b>\n\nCaptain scores ×2 points.\nNo captain = cannot confirm.",
            parse_mode="HTML", reply_markup=kb
        )


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

    visual   = build_squad_visual(squad, formation, pid)
    cap_name = p["name"] if p else pid
    await callback.message.edit_text(
        "⭐ Captain: <b>" + cap_name + "</b>\n\n📋 <b>Squad Review</b>\n\n" + visual,
        parse_mode="HTML",
        reply_markup=squad_review_keyboard(lang, confirmed=False)
    )
    await state.set_state(Squad.review)
    await callback.answer()


# ── Change captain (from My Squad) ────────────────────────────────────────────

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


# ── Confirm ───────────────────────────────────────────────────────────────────

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

    # Fallback to FSM state
    fsm = await state.get_data()
    if (not squad or not squad_is_complete(squad, formation)) and fsm.get("squad"):
        squad     = fsm["squad"]
        formation = fsm.get("formation", formation)
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


@router.callback_query(F.data == "squad:change_confirmed")
async def change_confirmed_squad(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    await sheets.update_user(uid, confirmed=False)
    await callback.message.edit_text(
        "🔄 <b>Change Team</b>\n\nChoose your new formation:",
        parse_mode="HTML",
        reply_markup=formation_keyboard(lang)
    )
    await state.set_state(Squad.formation)
    await callback.answer()
