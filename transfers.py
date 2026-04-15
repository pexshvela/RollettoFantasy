import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import config
import sheets
from states import Transfers
from translations import t
from players import get_player, fmt_price
from inline import transfer_squad_keyboard, player_list_keyboard, confirm_transfer_keyboard, home_keyboard
from helpers import get_lang

logger = logging.getLogger(__name__)
router = Router()
CURRENT_MATCHDAY = "QF"  # Update this each matchday: QF / SF / F


def _safe_budget(user):
    raw = (user or {}).get("budget_remaining", config.TOTAL_BUDGET)
    try:
        return int(float(raw or config.TOTAL_BUDGET))
    except (ValueError, TypeError):
        return config.TOTAL_BUDGET


@router.callback_query(F.data == "home:transfers")
async def transfers_menu(callback: CallbackQuery, state: FSMContext):
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    formation = (user or {}).get("formation", "4-3-3") or "4-3-3"
    free_used = await sheets.get_transfers_used(callback.from_user.id, CURRENT_MATCHDAY)
    free_remaining = max(0, config.FREE_TRANSFERS_PER_MATCHDAY - free_used)
    try:
        await callback.message.edit_text(
            t(lang, "transfer_menu", free=free_remaining),
            parse_mode="HTML",
            reply_markup=transfer_squad_keyboard(lang, squad_data, formation),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await state.set_state(Transfers.menu)
    await callback.answer()


@router.callback_query(F.data.startswith("transfer_out:"), Transfers.menu)
async def select_player_out(callback: CallbackQuery, state: FSMContext):
    _, pid_out, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    p_out = get_player(pid_out)
    position = p_out["position"] if p_out else "FW"
    await state.update_data(pid_out=pid_out, slot=slot, position=position)
    await callback.message.edit_text(
        t(lang, "select_player_in", pos=position),
        parse_mode="HTML",
        reply_markup=player_list_keyboard(lang, position, slot, 0, squad_data),
    )
    await state.set_state(Transfers.select_player_in)
    await callback.answer()


@router.callback_query(F.data.startswith("pick:"), Transfers.select_player_in)
async def select_player_in(callback: CallbackQuery, state: FSMContext):
    _, pid_in, slot = callback.data.split(":", 2)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    data = await state.get_data()
    pid_out = data.get("pid_out")
    p_in = get_player(pid_in)
    p_out = get_player(pid_out)
    if not p_in or not p_out:
        await callback.answer("Error — player not found.", show_alert=True)
        return
    budget = _safe_budget(user)
    price_diff = p_in["price"] - p_out["price"]
    if price_diff > budget:
        await callback.answer(t(lang, "no_budget"), show_alert=True)
        return
    free_used = await sheets.get_transfers_used(callback.from_user.id, CURRENT_MATCHDAY)
    is_free = free_used < config.FREE_TRANSFERS_PER_MATCHDAY
    cost_msg = t(lang, "transfer_free_cost") if is_free else t(lang, "transfer_points_cost")
    await state.update_data(pid_in=pid_in)
    await callback.message.edit_text(
        t(lang, "confirm_transfer", out=p_out["name"], **{"in": p_in["name"]}, cost_msg=cost_msg),
        parse_mode="HTML",
        reply_markup=confirm_transfer_keyboard(lang, pid_out, pid_in, slot),
    )
    await state.set_state(Transfers.confirming)
    await callback.answer()


@router.callback_query(F.data.startswith("transfer_confirm:"), Transfers.confirming)
async def confirm_transfer(callback: CallbackQuery, state: FSMContext):
    _, pid_out, pid_in, slot = callback.data.split(":", 3)
    user = await sheets.get_user(callback.from_user.id)
    lang = await get_lang(callback.from_user.id, user)
    squad_data = await sheets.get_squad(callback.from_user.id) or {}
    p_in = get_player(pid_in)
    p_out = get_player(pid_out)
    if not p_in or not p_out:
        await callback.answer("Error.", show_alert=True)
        return
    budget = _safe_budget(user)
    budget += p_out["price"]
    budget -= p_in["price"]
    squad_data[slot] = pid_in
    # Clear captain if transferred out
    if squad_data.get("captain") == pid_out or (user or {}).get("captain") == pid_out:
        squad_data["captain"] = ""
        await sheets.update_user(callback.from_user.id, captain="")
    await sheets.save_squad(callback.from_user.id, squad_data)
    await sheets.update_user(callback.from_user.id, budget_remaining=budget)
    # Count transfer and apply points penalty if needed
    free_used = await sheets.get_transfers_used(callback.from_user.id, CURRENT_MATCHDAY)
    is_free = free_used < config.FREE_TRANSFERS_PER_MATCHDAY
    cost_label = "free" if is_free else f"-{config.EXTRA_TRANSFER_COST_PTS}pts"
    await sheets.log_transfer(callback.from_user.id, CURRENT_MATCHDAY, pid_out, pid_in, cost_label)
    if not is_free:
        pts = int(float((user or {}).get("total_points", 0) or 0))
        await sheets.update_user(
            callback.from_user.id,
            total_points=max(0, pts - config.EXTRA_TRANSFER_COST_PTS)
        )
    submitted = ((user or {}).get("squad_submitted", "no") == "yes")
    await callback.message.edit_text(
        t(lang, "transfer_done"),
        parse_mode="HTML",
        reply_markup=home_keyboard(lang, callback.from_user.id, submitted, True),
    )
    await state.set_state(None)
    await callback.answer()
