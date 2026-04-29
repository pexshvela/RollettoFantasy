"""
transfers.py — Transfer window management.
Admin sets window open/close and free transfer count.
Users can transfer within the window.
Extra transfers cost -4pts each.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import sheets
import players as pl_module
from players import get_player, get_players_by_position, fmt_price
from states import Transfer
from translations import t
from helpers import (
    get_lang, get_all_slots, slot_to_position,
    build_squad_visual, calc_squad_cost, squad_is_complete
)
from inline import home_keyboard, transfer_pick_out_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "home:transfers")
async def show_transfers(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    # Check window
    window_open = await sheets.is_transfer_window_open()
    if not window_open:
        ts = await sheets.get_transfer_settings()
        close = ts.get("close") or "N/A"
        await callback.message.edit_text(
            t(lang, "transfers_closed"),
            parse_mode="HTML",
            reply_markup=home_keyboard(lang)
        )
        await callback.answer()
        return

    # Show squad with transfer options
    squad     = await sheets.get_squad(uid)
    formation = user.get("formation", "4-3-3")

    if not squad or not squad_is_complete(squad, formation):
        await callback.message.edit_text(
            t(lang, "no_squad"),
            reply_markup=home_keyboard(lang)
        )
        await callback.answer()
        return

    ts = await sheets.get_transfer_settings()
    free_n = ts.get("free", config.FREE_TRANSFERS_DEFAULT)

    gw = await sheets.get_active_gameweek()
    gw_id = gw["id"] if gw else 0
    used = await sheets.count_transfers_this_gw(uid, gw_id) if gw_id else 0
    remaining_free = max(0, (free_n if free_n != 0 else 999) - used)
    cost_next = 0 if remaining_free > 0 or free_n == 0 else config.EXTRA_TRANSFER_COST

    ts_settings = await sheets.get_transfer_settings()
    close_time  = (ts_settings.get("close") or "")[:16]

    lines = [
        t(lang, "transfers_open", close=close_time),
        t(lang, "free_transfers", n=("∞" if free_n == 0 else remaining_free)),
        "",
        "Select a player to <b>remove</b>:",
    ]

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=transfer_pick_out_keyboard(squad, formation, lang)
    )
    await state.update_data(gw_id=gw_id, used=used, free_n=free_n, squad=squad, formation=formation)
    await state.set_state(Transfer.pick_out)
    await callback.answer()


@router.callback_query(Transfer.pick_out, F.data.startswith("transfer:out:"))
async def pick_player_out(callback: CallbackQuery, state: FSMContext):
    _, _, pid_out, slot = callback.data.split(":")
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    p_out = get_player(pid_out)
    pos   = p_out["position"] if p_out else slot_to_position(slot)

    # Show available replacements
    budget_used = calc_squad_cost(data["squad"])
    budget_free = config.TOTAL_BUDGET - budget_used + (p_out["price"] if p_out else 0)

    available = [
        p for p in get_players_by_position(pos)
        if p["price"] <= budget_free and p["id"] not in data["squad"].values()
    ]

    kb = InlineKeyboardBuilder()
    for p in available[:20]:
        kb.button(
            text=f"{p['name']} ({p['team']}) — {fmt_price(p['price'])}",
            callback_data=f"transfer:in:{p['id']}"
        )
    kb.button(text=t(lang, "back"), callback_data="home:transfers")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    name_out = p_out["name"] if p_out else pid_out
    await callback.message.edit_text(
        f"❌ Removing: <b>{name_out}</b>\n\n"
        f"💰 Budget for replacement: {fmt_price(budget_free)}\n\n"
        f"Pick replacement <b>{pos}</b>:",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await state.update_data(pid_out=pid_out, slot_out=slot, pos=pos)
    await state.set_state(Transfer.pick_in)
    await callback.answer()


@router.callback_query(Transfer.pick_in, F.data.startswith("transfer:in:"))
async def pick_player_in(callback: CallbackQuery, state: FSMContext):
    pid_in = callback.data.split(":")[2]
    uid    = callback.from_user.id
    user   = await sheets.get_user(uid)
    lang   = await get_lang(uid, user)
    data   = await state.get_data()

    pid_out  = data["pid_out"]
    slot_out = data["slot_out"]
    gw_id    = data.get("gw_id", 0)
    used     = data.get("used", 0)
    free_n   = data.get("free_n", config.FREE_TRANSFERS_DEFAULT)

    p_out = get_player(pid_out)
    p_in  = get_player(pid_in)

    # Calculate cost
    remaining_free = max(0, (free_n if free_n != 0 else 999) - used)
    cost = 0 if remaining_free > 0 or free_n == 0 else config.EXTRA_TRANSFER_COST

    name_out = p_out["name"] if p_out else pid_out
    name_in  = p_in["name"]  if p_in  else pid_in

    # Confirm
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Confirm Transfer", callback_data="transfer:confirm")
    kb.button(text="❌ Cancel",          callback_data="home:transfers")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    cost_text = f"\n⚠️ This costs <b>{cost} pts</b>" if cost else ""

    await callback.message.edit_text(
        f"🔄 <b>Transfer</b>\n\n"
        f"❌ Out: <b>{name_out}</b>\n"
        f"✅ In:  <b>{name_in}</b>"
        f"{cost_text}\n\nConfirm?",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await state.update_data(pid_in=pid_in, cost=cost)
    await state.set_state(Transfer.confirm)
    await callback.answer()


@router.callback_query(Transfer.confirm, F.data == "transfer:confirm")
async def confirm_transfer(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    data = await state.get_data()

    pid_out  = data["pid_out"]
    pid_in   = data["pid_in"]
    slot_out = data["slot_out"]
    gw_id    = data.get("gw_id", 0)
    cost     = data.get("cost", 0)

    # Update squad
    squad = await sheets.get_squad(uid)
    if squad:
        squad[slot_out] = pid_in
        await sheets.save_squad(uid, squad)

    # Log transfer
    await sheets.log_transfer(uid, pid_out, pid_in, gw_id, cost)

    # Apply point cost
    if cost > 0:
        current_pts = int(user.get("total_points") or 0)
        await sheets.update_user(uid, total_points=current_pts - cost)
    else:
        pass  # no point cost for free transfers

    p_out = get_player(pid_out)
    p_in  = get_player(pid_in)
    name_out = p_out["name"] if p_out else pid_out
    name_in  = p_in["name"]  if p_in  else pid_in

    await callback.message.edit_text(
        t(lang, "transfer_done", **{"out": name_out, "in": name_in}),
        parse_mode="HTML",
        reply_markup=home_keyboard(lang)
    )
    await state.clear()
    await callback.answer()
