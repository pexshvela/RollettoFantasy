"""
squad.py - Squad building with FIXED 15 slots always:
gk1, gk2, def1-5, mf1-5, fw1-3
Formation determines which slots are starters vs bench at scoring time.
Squad menu shows slots grouped by position with formation label.
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
from helpers import get_lang, get_formation_slots, build_squad_visual, calc_squad_cost
from inline import home_keyboard, formation_keyboard, captain_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()

POS_EMOJI = {"GK": "🧤", "DEF": "🔵", "MF": "🟡", "FW": "🔴"}

# Fixed 15 slots always — matches Supabase columns
# Slot names match Supabase squads table columns
# Starters: gk1, def1..N, mf1..N, fw1..N (per formation)
# Bench: bench_gk + enough DEF/MF/FW to reach 2GK 5DEF 5MF 3FW = 15 total
def _all_slots_for(formation: str) -> list[tuple[str,str]]:
    d = get_formation_slots(formation)
    slots = [("gk1", "GK")]
    for i in range(1, d["DEF"]+1): slots.append((f"def{i}", "DEF"))
    for i in range(1, d["MF"]+1):  slots.append((f"mf{i}",  "MF"))
    for i in range(1, d["FW"]+1):  slots.append((f"fw{i}",  "FW"))
    # Bench: always 1 GK, then fill remaining to reach 5DEF 5MF 3FW
    slots.append(("bench_gk", "GK"))
    bench_def = 5 - d["DEF"]
    bench_mf  = 5 - d["MF"]
    bench_fw  = 3 - d["FW"]
    for i in range(1, bench_def+1):
        key = "bench_def" if i == 1 else f"bench_def{i}"
        slots.append((key, "DEF"))
    for i in range(1, bench_mf+1):
        key = "bench_mf" if i == 1 else f"bench_mf{i}"
        slots.append((key, "MF"))
    for i in range(1, bench_fw+1):
        key = "bench_fw" if i == 1 else f"bench_fw{i}"
        slots.append((key, "FW"))
    return slots


def _starter_slots(formation: str) -> list[str]:
    """Which slots are starters for this formation."""
    d = get_formation_slots(formation)
    starters = ["gk1"]
    for i in range(1, d["DEF"] + 1): starters.append(f"def{i}")
    for i in range(1, d["MF"]  + 1): starters.append(f"mf{i}")
    for i in range(1, d["FW"]  + 1): starters.append(f"fw{i}")
    return starters


def _is_complete(squad: dict, formation: str = "4-3-3") -> bool:
    """True if all 15 slots filled."""
    if not squad:
        return False
    slots = _all_slots_for(formation)
    if all(squad.get(s) for s, _ in slots):
        return True
    # Fallback: count filled player slots
    count = sum(1 for k, v in squad.items()
                if isinstance(v, str) and v and k not in ("formation", "telegram_id"))
    return count >= 15


def _slot_label(slot: str, pos: str, squad: dict, formation: str, captain: str) -> str:
    starters = _starter_slots(formation)
    pid = squad.get(slot, "")
    p   = get_player(pid) if pid else None

    if p:
        cap = " ⭐" if pid == captain else ""
        role = "" if slot in starters else " (sub)"
        return POS_EMOJI[pos] + cap + " " + p["name"] + role + " — " + fmt_price(p["price"])
    else:
        role = "" if slot in starters else " sub"
        return POS_EMOJI[pos] + role + " — tap to pick"


async def _show_squad_menu(message, lang: str, formation: str, squad: dict,
                            captain: str = "", edit: bool = True):
    budget_left = config.TOTAL_BUDGET - calc_squad_cost(squad)
    all_slots_local = _all_slots_for(formation)
    filled   = sum(1 for s, _ in all_slots_local if squad.get(s))
    complete = _is_complete(squad, formation)

    header = (
        "<b>My Squad — " + formation + "</b>\n"
        "💰 " + fmt_price(budget_left) + "  👥 " + str(filled) + "/15"
    )

    starters = _starter_slots(formation)
    all_slots = _all_slots_for(formation)
    kb = InlineKeyboardBuilder()

    bench_slots = [s for s, _ in all_slots if s not in starters]
    shown_bench = False

    for slot, pos in all_slots:
        if slot in bench_slots and not shown_bench:
            kb.button(text="── Substitutes ──", callback_data="squad:noop")
            shown_bench = True
        label = _slot_label(slot, pos, squad, formation, captain)
        kb.button(text=label, callback_data="slot:" + slot + ":0")

    if complete:
        if not captain:
            kb.button(text="⭐ Choose Captain (required)", callback_data="squad:pick_captain")
        else:
            kb.button(text="⭐ Change Captain",            callback_data="squad:pick_captain")
            kb.button(text="✅ Confirm Squad",             callback_data="squad:confirm")

    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    try:
        if edit:
            await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
        else:
            await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


async def _show_player_list(message, lang: str, squad: dict, slot: str,
                             pos: str, page: int = 0):
    budget_left = config.TOTAL_BUDGET - calc_squad_cost(squad)
    current_pid = squad.get(slot, "")
    current_p   = get_player(current_pid) if current_pid else None
    refund      = current_p["price"] if current_p else 0
    budget_left += refund

    picked_ids = {v for k, v in squad.items() if isinstance(v, str) and v and k != slot}

    # Show all players — unaffordable ones marked with 🚫
    available = [p for p in get_players_by_position(pos) if p["id"] not in picked_ids]
    available.sort(key=lambda p: -p["price"])

    page_size = 8
    start = page * page_size
    end   = start + page_size
    page_p = available[start:end]

    header = (
        POS_EMOJI[pos] + " <b>Pick " + pos + "</b>\n"
        "💰 Budget: " + fmt_price(budget_left)
        + ("\n↩️ Replacing: <b>" + current_p["name"] + "</b>" if current_p else "")
    )

    kb = InlineKeyboardBuilder()
    # Inline search button — opens dynamic search as user types
    from aiogram.types import InlineKeyboardButton
    search_btn = InlineKeyboardButton(
        text="🔍 Search player",
        switch_inline_query_current_chat="search:" + slot + ":" + pos + " "
    )
    kb.row(search_btn)
    for p in page_p:
        can_afford = p["price"] <= budget_left
        prefix = "" if can_afford else "🚫 "
        kb.button(
            text=prefix + p["name"] + " (" + p["team"] + ") — " + fmt_price(p["price"]),
            callback_data="pick:" + slot + ":" + p["id"]
        )
    if page > 0:
        kb.button(text="◀️ Prev", callback_data="slot:" + slot + ":" + str(page - 1))
    if end < len(available):
        kb.button(text="Next ▶️", callback_data="slot:" + slot + ":" + str(page + 1))
    kb.button(text="◀️ Back", callback_data="squad:list")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    try:
        await message.edit_text(header, parse_mode="HTML", reply_markup=kb.as_markup())
    except Exception:
        await message.answer(header, parse_mode="HTML", reply_markup=kb.as_markup())


def _slot_pos(slot: str) -> str:
    if "gk" in slot:  return "GK"
    if "def" in slot: return "DEF"
    if "mf" in slot:  return "MF"
    return "FW"


# ── Handlers ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:squad")
async def show_squad(callback: CallbackQuery, state: FSMContext):
    uid       = callback.from_user.id
    user      = await sheets.get_user(uid)
    lang      = await get_lang(uid, user)
    squad     = await sheets.get_squad(uid)
    formation = (user or {}).get("formation", "4-3-3")
    captain   = (user or {}).get("captain", "")
    # Check confirmation across ALL gameweeks, not just active one
    confirmed = False
    all_gws = await sheets.get_all_gameweeks()
    for gw in all_gws:
        conf = await sheets.get_confirmation(uid, gw["id"])
        if conf:
            confirmed = True
            break

    if squad and _is_complete(squad, formation):
        before_dl = await sheets.is_before_deadline()
        kb = InlineKeyboardBuilder()
        if confirmed:
            if before_dl:
                kb.button(text="⭐ Change Captain", callback_data="squad:pick_captain")
                kb.button(text="🔄 Change Team",    callback_data="squad:change_confirmed")
        else:
            if before_dl:
                kb.button(text="⭐ Change Captain", callback_data="squad:pick_captain")
                kb.button(text="✅ Confirm Squad",  callback_data="squad:confirm")
                kb.button(text="🔄 Rebuild Squad",  callback_data="squad:change")
        kb.button(text=t(lang, "back_home"), callback_data="home:back")
        kb.adjust(1)

        pts    = await sheets.get_squad_points_summary(uid)
        visual = build_squad_visual(squad, formation, captain, pts)
        status = "🔒 <b>Confirmed</b>" if confirmed else "⚠️ <b>Not confirmed</b>"
        await callback.message.edit_text(
            "📋 <b>My Squad</b>  " + status + "\n\n" + visual,
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
    elif squad and not _is_complete(squad, formation):
        # Partially built — resume
        await state.update_data(squad=squad, formation=formation, captain=captain)
        await _show_squad_menu(callback.message, lang, formation, squad, captain)
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
    captain   = (user or {}).get("captain", "")

    await state.update_data(formation=formation, squad={}, captain=captain)
    await sheets.update_user(uid, formation=formation)
    await _show_squad_menu(callback.message, lang, formation, {}, captain)
    await state.set_state(Squad.picking_gk)
    await callback.answer()


@router.callback_query(F.data == "squad:list")
async def squad_list(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    captain   = data.get("captain", (user or {}).get("captain", ""))
    squad     = data.get("squad", {})
    if not squad:
        db = await sheets.get_squad(uid)
        if db: squad = db
    await _show_squad_menu(callback.message, lang, formation, squad, captain)
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
    squad     = data.get("squad", {})
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    captain   = data.get("captain", (user or {}).get("captain", ""))
    if not squad:
        db = await sheets.get_squad(uid)
        if db:
            squad = db
            await state.update_data(squad=squad, formation=formation, captain=captain)
    await _show_player_list(callback.message, lang, squad, slot, pos, page)
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
    captain   = data.get("captain", (user or {}).get("captain", ""))
    squad     = dict(data.get("squad", {}))
    if not squad:
        db = await sheets.get_squad(uid)
        if db: squad = dict(db)

    p = get_player(pid)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return

    # Fix: validate position matches slot
    expected_pos = _slot_pos(slot)
    if p["position"] != expected_pos:
        await callback.answer(
            "❌ Wrong position! Slot needs " + expected_pos +
            " but " + p["name"] + " is a " + p["position"] + ".",
            show_alert=True
        )
        return

    current_pid = squad.get(slot, "")
    current_p   = get_player(current_pid) if current_pid else None
    refund      = current_p["price"] if current_p else 0
    budget_left = config.TOTAL_BUDGET - calc_squad_cost(squad) + refund

    if p["price"] > budget_left:
        await callback.answer(
            "❌ Insufficient funds! This player costs " + fmt_price(p["price"]) +
            " but you only have " + fmt_price(budget_left) + " left.",
            show_alert=True
        )
        return

    squad[slot] = pid
    await state.update_data(squad=squad)

    await callback.answer("✅ " + p["name"] + " added!", show_alert=False)

    # Collapse the inline result message to just a confirmation line
    try:
        await callback.message.edit_text(
            "✅ <b>" + p["name"] + "</b> added to squad.",
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception:
        pass

    # Send fresh squad menu as new message
    await _show_squad_menu(callback.message, lang, formation, squad, captain, edit=False)


# ── Search ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("search_player:"))
async def search_player_prompt(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    slot, pos = parts[1], parts[2]
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    await state.update_data(search_slot=slot, search_pos=pos)
    await state.set_state(Squad.searching)

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Cancel", callback_data="slot:" + slot + ":0")
    kb.adjust(1)

    try:
        await callback.message.edit_text(
        await callback.message.edit_text(
            "🔍 <b>Search player</b>\n\nType a player name:",
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
        )
    except Exception:
        await callback.message.answer(
        await callback.message.answer(
            "🔍 <b>Search player</b>\n\nType a player name:",
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
        )
    await callback.answer()


@router.message(Squad.searching)
async def search_player_results(message, state: FSMContext):
    from aiogram.types import Message as AioMessage
    uid  = message.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    slot      = data.get("search_slot", "")
    pos       = data.get("search_pos", "GK")
    query     = message.text.strip().lower()
    squad     = data.get("squad", {})
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))

    if not squad:
        db = await sheets.get_squad(uid)
        if db: squad = db

    budget_left = config.TOTAL_BUDGET - calc_squad_cost(squad)
    current_pid = squad.get(slot, "")
    current_p   = get_player(current_pid) if current_pid else None
    if current_p:
        budget_left += current_p["price"]

    picked_ids = {v for k, v in squad.items() if isinstance(v, str) and v and k != slot}

    # Search all players of this position
    results = [
        p for p in get_players_by_position(pos)
        if query in p["name"].lower() or query in p["team"].lower()
        if p["id"] not in picked_ids
    ]
    results.sort(key=lambda p: -p["price"])

    kb = InlineKeyboardBuilder()
    if not results:
        kb.button(text="No players found", callback_data="squad:noop")
    else:
        for p in results[:10]:
            can_afford = p["price"] <= budget_left
            label = ("" if can_afford else "🚫 ") + p["name"] + " (" + p["team"] + ") — " + fmt_price(p["price"])
            kb.button(text=label, callback_data="pick:" + slot + ":" + p["id"])

    kb.button(text="🔍 Search again", callback_data="search_player:" + slot + ":" + pos)
    kb.button(text="◀️ Back to list",  callback_data="slot:" + slot + ":0")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    await message.answer(
        "🔍 Results for <b>" + message.text + "</b>:",
        parse_mode="HTML", reply_markup=kb.as_markup()
    )


# ── Captain ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "squad:pick_captain")
async def go_pick_captain(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return
    data      = await state.get_data()
    squad     = data.get("squad", {})
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    if not squad:
        db = await sheets.get_squad(uid)
        if db:
            squad = db
            await state.update_data(squad=squad, formation=formation)
    kb = captain_keyboard(squad, formation, lang)
    await callback.message.edit_text(
        "⭐ <b>Choose your captain</b>\n\nCaptain scores ×2 points.",
        parse_mode="HTML", reply_markup=kb
    )
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
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    p = get_player(pid)

    await sheets.update_user(uid, captain=pid)
    await state.update_data(captain=pid)

    await _show_squad_menu(callback.message, lang, formation, squad, pid)
    await state.set_state(Squad.picking_gk)
    await callback.answer()


# ── Confirm ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "squad:confirm")
async def confirm_squad(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    captain = data.get("captain", (user or {}).get("captain", ""))
    if not captain:
        await callback.answer(t(lang, "no_captain"), show_alert=True)
        return
    if not await sheets.is_before_deadline():
        await callback.answer(t(lang, "deadline_passed"), show_alert=True)
        return

    squad     = data.get("squad", {})
    formation = data.get("formation", (user or {}).get("formation", "4-3-3"))
    if not squad:
        squad = await sheets.get_squad(uid)
    if not squad or not _is_complete(squad, formation):
        await callback.answer(t(lang, "no_squad"), show_alert=True)
        return

    gw = await sheets.get_active_gameweek()
    if not gw:
        await callback.answer("No active gameweek. Admin needs to run /fixtures first.", show_alert=True)
        return

    await sheets.save_squad(uid, dict(squad, formation=formation))
    await sheets.confirm_squad(uid, gw["id"], squad)
    import config as _config
    await callback.message.edit_text(
        t(lang, "squad_confirmed"), parse_mode="HTML",
        reply_markup=home_keyboard(lang, is_admin=uid == _config.ADMIN_ID)
    )
    await callback.answer()


# ── Change / Rebuild ──────────────────────────────────────────────────────────

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
    squad     = await sheets.get_squad(uid)
    formation = (user or {}).get("formation", "4-3-3")
    captain   = (user or {}).get("captain", "")
    await state.update_data(squad=squad or {}, formation=formation, captain=captain)
    if squad:
        await _show_squad_menu(callback.message, lang, formation, squad, captain)
    else:
        await callback.message.edit_text(
            t(lang, "build_squad"), parse_mode="HTML",
            reply_markup=formation_keyboard(lang)
        )
        await state.set_state(Squad.formation)
    await callback.answer()
