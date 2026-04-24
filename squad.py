"""
squad.py — Squad building with free-choice player selection.
User picks any player in any order from a full list filtered by position needs.
Formation determines how many of each position are needed.
Bench must fill exactly: 1 GK, 1 DEF, 1 MF, 1 FW.
Captain required before confirmation.
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
    get_bench_slots, get_all_slots, slot_to_position,
    build_squad_visual, calc_squad_cost, squad_is_complete, FORMATIONS
)
from inline import home_keyboard, formation_keyboard, captain_keyboard, squad_review_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()

# Position needs per formation (starters) + bench always = 1 GK, 1 DEF, 1 MF, 1 FW
BENCH_NEEDS = {"GK": 1, "DEF": 1, "MF": 1, "FW": 1}


def _squad_needs(formation: str, current_squad: dict) -> dict[str, int]:
    """Return how many more of each position are still needed."""
    slots_def = get_formation_slots(formation)
    # Starter needs
    needs = {"GK": 1, "DEF": slots_def["DEF"], "MF": slots_def["MF"], "FW": slots_def["FW"]}
    # Add bench needs
    for pos, n in BENCH_NEEDS.items():
        needs[pos] = needs.get(pos, 0) + n

    # Count what's already picked
    for pid in current_squad.values():
        if isinstance(pid, str) and pid:
            p = get_player(pid)
            if p:
                pos = p["position"]
                needs[pos] = max(0, needs.get(pos, 0) - 1)
    return needs


def _all_positions_filled(formation: str, current_squad: dict) -> bool:
    needs = _squad_needs(formation, current_squad)
    return all(v == 0 for v in needs.values())


def _assign_slot(formation: str, current_squad: dict, pid: str, pos: str) -> dict:
    """Assign player to the next available slot for their position."""
    squad = dict(current_squad)
    slots_def = get_formation_slots(formation)

    # Determine starter slot count for this position
    if pos == "GK":
        starter_count = 1
    else:
        starter_count = slots_def.get(pos, 0)

    # Count how many starters of this pos are already filled
    starter_slots = [f"gk1"] if pos == "GK" else [f"{pos.lower()}{i}" for i in range(1, starter_count + 1)]
    bench_slot    = f"bench_{pos.lower()}"

    # Try to fill a starter slot first
    for slot in starter_slots:
        if not squad.get(slot):
            squad[slot] = pid
            return squad

    # Then fill bench slot
    if not squad.get(bench_slot):
        squad[bench_slot] = pid
        return squad

    return squad  # shouldn't happen if needs check is correct


async def _show_picker(message, lang: str, formation: str,
                       current_squad: dict, page: int = 0):
    """Show all available players the user can still pick."""
    needs       = _squad_needs(formation, current_squad)
    budget_used = calc_squad_cost(current_squad)
    budget_left = config.TOTAL_BUDGET - budget_used
    picked_ids  = set(v for v in current_squad.values() if isinstance(v, str) and v)

    # Build available players across all positions still needed
    available = []
    for pos, count in needs.items():
        if count > 0:
            for p in get_players_by_position(pos):
                if p["id"] not in picked_ids and p["price"] <= budget_left:
                    available.append(p)

    # Sort by position then price desc
    pos_order = {"GK": 0, "DEF": 1, "MF": 2, "FW": 3}
    available.sort(key=lambda p: (pos_order.get(p["position"], 9), -p["price"]))

    # Pagination
    page_size = 8
    start = page * page_size
    end   = start + page_size
    page_players = available[start:end]

    # Build status header
    needs_text = " | ".join(
        f"{pos}: {n}" for pos, n in needs.items() if n > 0
    )
    total_picked = sum(1 for v in current_squad.values() if isinstance(v, str) and v)
    total_needed = sum(needs.values()) + total_picked

    header = (
        f"📋 <b>Build Your Squad</b> — {formation}\n"
        f"💰 Budget left: {fmt_price(budget_left)}\n"
        f"👥 Picked: {total_picked}/{total_needed}\n"
        f"Still need: {needs_text}"
    )

    kb = InlineKeyboardBuilder()
    pos_emoji = {"GK": "🧤", "DEF": "🔵", "MF": "🟡", "FW": "🔴"}
    for p in page_players:
        label = f"{pos_emoji.get(p['position'],'⚪')} {p['name']} ({p['team']}) — {fmt_price(p['price'])}"
        kb.button(text=label, callback_data=f"pick:{p['position']}:{p['id']}")

    # Pagination
    nav = []
    if page > 0:
        nav.append(("◀️ Prev", f"squad_page:{page-1}"))
    if end < len(available):
        nav.append(("Next ▶️", f"squad_page:{page+1}"))
    for label, cb in nav:
        kb.button(text=label, callback_data=cb)

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


# ── Formation selection ───────────────────────────────────────────────────────

@router.callback_query(Squad.formation, F.data.startswith("formation:"))
async def pick_formation(callback: CallbackQuery, state: FSMContext):
    uid       = callback.from_user.id
    user      = await sheets.get_user(uid)
    lang      = await get_lang(uid, user)
    formation = callback.data.split(":")[1]

    await state.update_data(formation=formation, squad={})
    await sheets.update_user(uid, formation=formation)
    await _show_picker(callback.message, lang, formation, {})
    await state.set_state(Squad.picking_gk)  # reuse state for "picking"
    await callback.answer()


# ── Player picking (any order) ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("squad_page:"))
async def paginate(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    await _show_picker(callback.message, lang, data.get("formation","4-3-3"),
                       data.get("squad",{}), page)
    await callback.answer()


@router.callback_query(
    F.data.startswith("pick:"),
    Squad.picking_gk  # handles all picking states
)
async def pick_player(callback: CallbackQuery, state: FSMContext):
    _, pos, pid = callback.data.split(":")
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    formation = data.get("formation", "4-3-3")
    squad     = dict(data.get("squad", {}))

    # Check still needed
    needs = _squad_needs(formation, squad)
    if needs.get(pos, 0) <= 0:
        await callback.answer(f"You don't need more {pos} players.", show_alert=True)
        return

    # Check budget
    p = get_player(pid)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return
    budget_used = calc_squad_cost(squad)
    if budget_used + p["price"] > config.TOTAL_BUDGET:
        await callback.answer(t(lang, "over_budget"), show_alert=True)
        return

    # Assign to slot
    squad = _assign_slot(formation, squad, pid, pos)
    await state.update_data(squad=squad)

    # Check if complete
    if _all_positions_filled(formation, squad):
        await sheets.save_squad(uid, {**squad, "formation": formation})
        await _show_captain_picker(callback.message, lang, squad, formation)
        await state.set_state(Squad.captain)
    else:
        await _show_picker(callback.message, lang, formation, squad)

    await callback.answer()


# Register pick handler for all squad-related states
for _s in [Squad.picking_def, Squad.picking_mf, Squad.picking_fw, Squad.picking_bench]:
    router.callback_query.register(
        pick_player, F.data.startswith("pick:"), _s
    )


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
    await callback.message.edit_text(
        f"✅ Captain: <b>{p['name'] if p else pid}</b>\n\n📋 <b>Squad Review</b>\n\n{visual}",
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
    from inline import home_keyboard
    await callback.message.edit_text(
        t(lang, "squad_confirmed"),
        parse_mode="HTML",
        reply_markup=home_keyboard(lang, is_admin=uid == _config.ADMIN_ID)
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "squad:change")
async def change_player(callback: CallbackQuery, state: FSMContext):
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
    from inline import home_keyboard
    await callback.message.edit_text(
        t(lang, "squad_confirmed"),
        parse_mode="HTML",
        reply_markup=home_keyboard(lang, is_admin=uid == _config.ADMIN_ID)
    )
    await callback.answer()
