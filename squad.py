"""
squad.py — Simple vertical slot list for squad building.
Each slot is a button. Tap to pick or replace a player.
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
    get_lang, get_formation_slots, build_squad_visual,
    calc_squad_cost, squad_is_complete, FORMATIONS
)
from inline import home_keyboard, formation_keyboard, captain_keyboard, squad_review_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()

POS_EMOJI = {"GK": "🧤", "DEF": "🔵", "MF": "🟡", "FW": "🔴"}
POS_NAME  = {"GK": "GK", "DEF": "DEF", "MF": "MID", "FW": "FWD"}


def _slots_for_formation(formation: str) -> list[tuple[str, str]]:
    """
    Squad is always: 2 GK, 5 DEF, 5 MF, 3 FW = 15 players.
    Formation only determines which 11 start — reflected in slot naming.
    Starters: 1 GK + formation DEF/MF/FW
    Bench: remaining players to reach 2 GK, 5 DEF, 5 MF, 3 FW totals
    """
    d = get_formation_slots(formation)  # starter DEF/MF/FW counts

    slots = []

    # Starter GK
    slots.append(("gk1", "GK"))

    # Starter DEF, MF, FW per formation
    for i in range(1, d["DEF"] + 1): slots.append((f"def{i}", "DEF"))
    for i in range(1, d["MF"]  + 1): slots.append((f"mf{i}",  "MF"))
    for i in range(1, d["FW"]  + 1): slots.append((f"fw{i}",  "FW"))

    # Bench: fill remaining to reach 2 GK, 5 DEF, 5 MF, 3 FW
    bench_gk  = 2 - 1                  # always 1 bench GK
    bench_def = 5 - d["DEF"]           # remaining DEF
    bench_mf  = 5 - d["MF"]            # remaining MF
    bench_fw  = 3 - d["FW"]            # remaining FW

    slots.append(("bench_gk", "GK"))
    for i in range(1, bench_def + 1): slots.append((f"bench_def{i}", "DEF"))
    for i in range(1, bench_mf  + 1): slots.append((f"bench_mf{i}",  "MF"))
    for i in range(1, bench_fw  + 1): slots.append((f"bench_fw{i}",  "FW"))

    return slots


async def _show_squad_menu(message, lang: str, formation: str, squad: dict,
                            edit: bool = True, show_confirm: bool = False):
    """Show the full squad as a vertical button list."""
    slots       = _slots_for_formation(formation)
    budget_used = calc_squad_cost(squad)
    budget_left = config.TOTAL_BUDGET - budget_used
    filled      = sum(1 for s, _ in slots if squad.get(s))
    complete    = filled == len(slots)

    header = (
        "<b>Build Squad — " + formation + "</b>\n"
        "💰 " + fmt_price(budget_left) + " left  👥 " + str(filled) + "/" + str(len(slots))
    )

    kb = InlineKeyboardBuilder()
    bench_started = False
    for slot, pos in slots:
        if slot.startswith("bench_") and not bench_started:
            kb.button(text="── Substitutes ──", callback_data="squad:noop")
            bench_started = True

        pid = squad.get(slot, "")
        p   = get_player(pid) if pid else None
        if p:
            label = POS_EMOJI[pos] + " " + p["name"] + " — " + fmt_price(p["price"])
        else:
            label = POS_EMOJI[pos] + " " + POS_NAME[pos] + " — tap to pick"

        kb.button(text=label, callback_data="slot:" + slot + ":0")

    # Show captain + confirm buttons when squad is complete
    if complete or show_confirm:
        kb.button(text="⭐ Set Captain", callback_data="squad:pick_captain")
        kb.button(text="✅ Confirm Squad", callback_data="squad:confirm")

    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    try:
        if edit:
            await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
        else:
            await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


async def _show_player_list(message, lang: str, formation: str, squad: dict,
                             slot: str, pos: str, page: int = 0):
    """Show paginated player list for a slot."""
    budget_used = calc_squad_cost(squad)
    budget_left = config.TOTAL_BUDGET - budget_used

    # Refund current player in this slot
    current_pid = squad.get(slot, "")
    current_p   = get_player(current_pid) if current_pid else None
    if current_p:
        budget_left += current_p["price"]

    picked_ids = {v for k, v in squad.items() if isinstance(v, str) and v and k != slot}

    available = [
        p for p in get_players_by_position(pos)
        if p["id"] not in picked_ids and p["price"] <= budget_left
    ]
    available.sort(key=lambda p: -p["price"])

    page_size = 8
    start  = page * page_size
    end    = start + page_size
    page_p = available[start:end]

    is_bench = slot.startswith("bench_")
    slot_label = ("Sub " if is_bench else "") + POS_NAME[pos]
    header = (
        POS_EMOJI[pos] + " <b>" + slot_label + "</b>\n"
        "💰 Budget: " + fmt_price(budget_left)
        + ("\n↩️ Replacing: <b>" + current_p["name"] + "</b>" if current_p else "")
    )

    kb = InlineKeyboardBuilder()
    for p in page_p:
        kb.button(
            text=p["name"] + " (" + p["team"] + ") — " + fmt_price(p["price"]),
            callback_data="pick:" + slot + ":" + p["id"]
        )

    if page > 0:
        kb.button(text="◀️ Prev", callback_data="slot:" + slot + ":" + str(page - 1))
    if end < len(available):
        kb.button(text="Next ▶️", callback_data="slot:" + slot + ":" + str(page + 1))

    kb.button(text="◀️ Back to squad", callback_data="squad:list")
    kb.button(text=t(lang, "back_home"),   callback_data="home:back")
    kb.adjust(1)

    try:
        await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slot_pos(slot: str) -> str:
    if "gk" in slot:  return "GK"
    if "def" in slot: return "DEF"
    if "mf" in slot:  return "MF"
    return "FW"


def _all_filled(formation: str, squad: dict) -> bool:
    return all(squad.get(s) for s, _ in _slots_for_formation(formation))


# ── Handlers ──────────────────────────────────────────────────────────────────

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
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
    else:
        # Squad exists in DB but slot names may not match — show squad menu anyway
        if squad and len([v for k,v in squad.items() if isinstance(v,str) and v and k!="formation"]) > 0:
            await state.update_data(squad=squad, formation=formation)
            await _show_squad_menu(callback.message, lang, formation, squad,
                                   show_confirm=_all_filled(formation, squad))
        else:
            # Check FSM
            fsm = await state.get_data()
            fsm_squad = fsm.get("squad", {})
            fsm_form  = fsm.get("formation", formation)
            if fsm_squad:
                await _show_squad_menu(callback.message, lang, fsm_form, fsm_squad,
                                       show_confirm=_all_filled(fsm_form, fsm_squad))
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
    await _show_squad_menu(callback.message, lang, formation, {})
    await state.set_state(Squad.picking_gk)
    await callback.answer()


@router.callback_query(F.data == "squad:list")
async def squad_list(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    squad     = data.get("squad", {})
    if not squad:
        db = await sheets.get_squad(uid)
        if db: squad = db
    await _show_squad_menu(callback.message, lang, formation, squad)
    await callback.answer()


@router.callback_query(F.data == "squad:noop")
async def noop(callback: CallbackQuery, state: FSMContext):
    await callback.answer()


@router.callback_query(F.data.startswith("slot:"))
async def open_slot(callback: CallbackQuery, state: FSMContext):
    parts     = callback.data.split(":")
    slot, page = parts[1], int(parts[2])
    pos       = _slot_pos(slot)
    uid       = callback.from_user.id
    user      = await sheets.get_user(uid)
    lang      = await get_lang(uid, user)
    data      = await state.get_data()
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    squad     = data.get("squad", {})
    if not squad:
        db = await sheets.get_squad(uid)
        if db:
            squad = db
            await state.update_data(squad=squad, formation=formation)
    await _show_player_list(callback.message, lang, formation, squad, slot, pos, page)
    await callback.answer()


@router.callback_query(F.data.startswith("pick:"))
async def pick_player(callback: CallbackQuery, state: FSMContext):
    parts     = callback.data.split(":")
    slot, pid = parts[1], parts[2]
    uid       = callback.from_user.id
    user      = await sheets.get_user(uid)
    lang      = await get_lang(uid, user)
    data      = await state.get_data()
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    squad     = dict(data.get("squad", {}))
    if not squad:
        db = await sheets.get_squad(uid)
        if db: squad = dict(db)

    p = get_player(pid)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return

    # Budget with refund of replaced player
    current_pid = squad.get(slot, "")
    current_p   = get_player(current_pid) if current_pid else None
    refund      = current_p["price"] if current_p else 0
    budget_left = config.TOTAL_BUDGET - calc_squad_cost(squad) + refund

    if p["price"] > budget_left:
        await callback.answer(t(lang, "over_budget"), show_alert=True)
        return

    squad[slot] = pid
    await state.update_data(squad=squad)

    await sheets.save_squad(uid, dict(squad, formation=formation))
    if _all_filled(formation, squad):
        captain = (user or {}).get("captain", "")
        if not captain:
            await _show_captain_picker(callback.message, lang, squad, formation)
            await state.set_state(Squad.captain)
        else:
            await _show_squad_menu(callback.message, lang, formation, squad, show_confirm=True)
    else:
        await _show_squad_menu(callback.message, lang, formation, squad)

    await callback.answer()


# ── Captain ───────────────────────────────────────────────────────────────────

async def _show_captain_picker(message, lang, squad, formation):
    kb = captain_keyboard(squad, formation, lang)
    txt = "⭐ <b>Choose your captain</b>\n\nCaptain scores ×2 points.\nNo captain = cannot confirm."
    try:
        await message.edit_text(txt, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await message.answer(txt, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "squad:pick_captain")
async def go_pick_captain(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()
    squad     = data.get("squad", {})
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    if not squad:
        db = await sheets.get_squad(uid)
        if db:
            squad = db
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
    await callback.message.edit_text(
        "⭐ Captain: <b>" + (p["name"] if p else pid) + "</b>\n\n📋 <b>Squad Review</b>\n\n" + visual,
        parse_mode="HTML",
        reply_markup=squad_review_keyboard(lang, confirmed=False)
    )
    await state.set_state(Squad.review)
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
    fsm       = await state.get_data()
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
    # Load existing squad and show it for editing
    squad     = await sheets.get_squad(uid)
    formation = (user or {}).get("formation", "4-3-3")
    await state.update_data(squad=squad or {}, formation=formation)
    if squad:
        await _show_squad_menu(callback.message, lang, formation, squad,
                               show_confirm=_all_filled(formation, squad))
    else:
        await callback.message.edit_text(
            t(lang, "build_squad"), parse_mode="HTML",
            reply_markup=formation_keyboard(lang)
        )
        await state.set_state(Squad.formation)
    await callback.answer()
