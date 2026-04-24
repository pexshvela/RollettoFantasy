"""
squad.py — Squad building flow:
1. Choose formation
2. See position buttons (GK/DEF/MF/FW) with count needed
3. Tap a position → see players for that position
4. Pick player → back to position menu
5. Once all filled → pick captain
6. Review → confirm (no captain = no confirm)
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
    get_bench_slots, build_squad_visual, calc_squad_cost,
    squad_is_complete, FORMATIONS
)
from inline import home_keyboard, formation_keyboard, captain_keyboard, squad_review_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()

POS_EMOJI = {"GK": "🧤", "DEF": "🔵", "MF": "🟡", "FW": "🔴"}
POS_NAME  = {"GK": "Goalkeeper", "DEF": "Defender", "MF": "Midfielder", "FW": "Forward"}

BENCH_NEEDS = {"GK": 1, "DEF": 1, "MF": 1, "FW": 1}


def _needs(formation: str, squad: dict) -> dict[str, int]:
    """How many more of each position are needed."""
    slots_def = get_formation_slots(formation)
    total = {
        "GK":  1 + 1,  # 1 starter + 1 bench
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


def _all_filled(formation: str, squad: dict) -> bool:
    return all(v == 0 for v in _needs(formation, squad).values())


def _assign_slot(formation: str, squad: dict, pid: str, pos: str) -> dict:
    """Put player into next free slot for their position."""
    squad = dict(squad)
    slots_def = get_formation_slots(formation)

    starter_slots = (
        ["gk1"] if pos == "GK"
        else [f"{pos.lower()}{i}" for i in range(1, slots_def.get(pos, 0) + 1)]
    )
    bench_slot = f"bench_{pos.lower()}"

    for slot in starter_slots:
        if not squad.get(slot):
            squad[slot] = pid
            return squad
    if not squad.get(bench_slot):
        squad[bench_slot] = pid
    return squad


# ── Position menu ─────────────────────────────────────────────────────────────

async def _show_position_menu(message, lang: str, formation: str,
                               squad: dict, edit: bool = True):
    needs       = _needs(formation, squad)
    budget_used = calc_squad_cost(squad)
    budget_left = config.TOTAL_BUDGET - budget_used
    total_need  = sum(_needs(formation, {}).values())
    picked      = sum(1 for v in squad.values() if isinstance(v, str) and v)

    header = (
        f"⚽ <b>Build Squad — {formation}</b>\n"
        f"💰 Budget left: {fmt_price(budget_left)}\n"
        f"👥 Players picked: {picked}/{total_need}\n\n"
        f"Choose a position to add a player:"
    )

    kb = InlineKeyboardBuilder()
    for pos in ["GK", "DEF", "MF", "FW"]:
        n = needs[pos]
        if n > 0:
            label = f"{POS_EMOJI[pos]} {POS_NAME[pos]} — {n} more needed"
        else:
            label = f"{POS_EMOJI[pos]} {POS_NAME[pos]} ✅"
        kb.button(text=label, callback_data=f"pos_pick:{pos}:0")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    try:
        if edit:
            await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
        else:
            await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


# ── Player list for a position ────────────────────────────────────────────────

async def _show_position_players(message, lang: str, formation: str,
                                  squad: dict, pos: str, page: int = 0):
    needs       = _needs(formation, squad)
    budget_used = calc_squad_cost(squad)
    budget_left = config.TOTAL_BUDGET - budget_used
    picked_ids  = {v for v in squad.values() if isinstance(v, str) and v}

    if needs.get(pos, 0) <= 0:
        await _show_position_menu(message, lang, formation, squad)
        return

    available = [
        p for p in get_players_by_position(pos)
        if p["id"] not in picked_ids and p["price"] <= budget_left
    ]
    available.sort(key=lambda p: -p["price"])

    page_size = 8
    start = page * page_size
    end   = start + page_size
    page_p = available[start:end]

    header = (
        f"{POS_EMOJI[pos]} <b>{POS_NAME[pos]}s</b> — {needs[pos]} more needed\n"
        f"💰 Budget left: {fmt_price(budget_left)}"
    )

    kb = InlineKeyboardBuilder()
    for p in page_p:
        label = f"{p['name']} ({p['team']}) — {fmt_price(p['price'])}"
        kb.button(text=label, callback_data=f"pick:{pos}:{p['id']}")

    nav = []
    if page > 0:
        nav.append(("◀️ Prev", f"pos_pick:{pos}:{page-1}"))
    if end < len(available):
        nav.append(("Next ▶️", f"pos_pick:{pos}:{page+1}"))
    for lbl, cb in nav:
        kb.button(text=lbl, callback_data=cb)

    kb.button(text="◀️ Back to positions", callback_data="squad:positions")
    kb.button(text=t(lang, "back_home"),    callback_data="home:back")
    kb.adjust(1)

    try:
        await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


# ── Entry points ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:squad")
async def show_squad(callback: CallbackQuery, state: FSMContext):
    uid   = callback.from_user.id
    user  = await sheets.get_user(uid)
    lang  = await get_lang(uid, user)
    squad = await sheets.get_squad(uid)
    formation = (user or {}).get("formation", "4-3-3")

    if squad and squad_is_complete(squad, formation):
        captain_id = (user or {}).get("captain", "")
        pts        = await sheets.get_squad_points_summary(uid)
        visual     = build_squad_visual(squad, formation, captain_id, pts)
        await callback.message.edit_text(
            f"📋 <b>My Squad</b>\n\n{visual}",
            parse_mode="HTML",
            reply_markup=squad_review_keyboard(lang, confirmed=(user or {}).get("confirmed", False))
        )
    else:
        await callback.message.edit_text(
            t(lang, "build_squad"),
            parse_mode="HTML",
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


@router.callback_query(F.data.startswith("pos_pick:"))
async def show_pos_players(callback: CallbackQuery, state: FSMContext):
    _, pos, page_str = callback.data.split(":")
    page = int(page_str)
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()
    await _show_position_players(callback.message, lang,
                                  data.get("formation", "4-3-3"),
                                  data.get("squad", {}), pos, page)
    await callback.answer()


@router.callback_query(F.data.startswith("pick:"))
async def pick_player(callback: CallbackQuery, state: FSMContext):
    _, pos, pid = callback.data.split(":")
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    formation = data.get("formation", "4-3-3")
    squad     = dict(data.get("squad", {}))
    needs     = _needs(formation, squad)

    if needs.get(pos, 0) <= 0:
        await callback.answer(f"You don't need more {POS_NAME.get(pos, pos)}s.", show_alert=True)
        return

    p = get_player(pid)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return

    budget_left = config.TOTAL_BUDGET - calc_squad_cost(squad)
    if p["price"] > budget_left:
        await callback.answer(t(lang, "over_budget"), show_alert=True)
        return

    squad = _assign_slot(formation, squad, pid, pos)
    await state.update_data(squad=squad)

    if _all_filled(formation, squad):
        await sheets.save_squad(uid, {**squad, "formation": formation})
        await _show_captain_picker(callback.message, lang, squad, formation)
        await state.set_state(Squad.captain)
    else:
        await _show_position_menu(callback.message, lang, formation, squad)

    await callback.answer()


# ── Captain ───────────────────────────────────────────────────────────────────

async def _show_captain_picker(message, lang: str, squad: dict, formation: str):
    kb = captain_keyboard(squad, formation, lang)
    try:
        await message.edit_text(
            "⭐ <b>Choose your captain</b>\n\nCaptain scores ×2 points.\nYou cannot confirm without a captain.",
            parse_mode="HTML", reply_markup=kb
        )
    except Exception:
        await message.answer(
            "⭐ <b>Choose your captain</b>\n\nCaptain scores ×2 points.\nYou cannot confirm without a captain.",
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
    await sheets.save_squad(uid, {**squad, "formation": formation})

    visual = build_squad_visual(squad, formation, pid)
    await callback.message.edit_text(
        f"⭐ Captain: <b>{p['name'] if p else pid}</b>\n\n📋 <b>Squad Review</b>\n\n{visual}",
        parse_mode="HTML",
        reply_markup=squad_review_keyboard(lang, confirmed=False)
    )
    await state.set_state(Squad.review)
    await callback.answer()


# ── Confirm / Change ──────────────────────────────────────────────────────────

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
        t(lang, "squad_confirmed"),
        parse_mode="HTML",
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
        t(lang, "build_squad"),
        parse_mode="HTML",
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
        t(lang, "squad_confirmed"),
        parse_mode="HTML",
        reply_markup=home_keyboard(lang, is_admin=uid == _config.ADMIN_ID)
    )
    await callback.answer()
