"""
stats.py — My Stats and Match Results handlers
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

import sheets
from states import Stats
from translations import t
from players import get_player, fmt_price
from helpers import get_lang

logger = logging.getLogger(__name__)
router = Router()


# ── My Stats ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:stats")
async def show_stats(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    squad = await sheets.get_squad(uid) or {}

    # Get total points per player
    summary = await sheets.get_squad_points_summary(uid)
    total_user_pts = sum(summary.values())

    if not summary and not squad:
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "back_home"), callback_data="home:back")
        await callback.message.edit_text(
            "📊 <b>My Stats</b>\n\nNo squad or points yet.",
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
        await callback.answer()
        return

    captain_id = (user or {}).get("captain", "")

    # Build player list — starting 11 only
    try:
        formation = (user or {}).get("formation", "4-3-3") or "4-3-3"
        parts = formation.split("-")
        n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        n_def, n_mid, n_fwd = 4, 3, 3

    starter_slots = (
        ["gk1"] +
        [f"def{i}" for i in range(1, n_def + 1)] +
        [f"mf{i}" for i in range(1, n_mid + 1)] +
        [f"fw{i}" for i in range(1, n_fwd + 1)]
    )

    kb = InlineKeyboardBuilder()
    lines = [f"📊 <b>My Squad Stats</b>\n🏆 Total: <b>{total_user_pts} pts</b>\n"]

    for slot in starter_slots:
        pid = squad.get(slot)
        if not pid:
            continue
        p = get_player(pid)
        if not p:
            continue
        pts = summary.get(pid, 0)
        cap = " ⭐" if pid == captain_id else ""
        pos_emoji = {"GK": "🧤", "DEF": "🔵", "MF": "🟡", "FW": "🔴"}.get(p["position"], "⚽")
        lines.append(f"{pos_emoji} {p['name']}{cap} — <b>{pts} pts</b>")
        kb.button(
            text=f"{p['name']}{cap} ({pts} pts)",
            callback_data=f"stats:player:{pid}"
        )

    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await state.set_state(Stats.viewing)
    await callback.answer()


@router.callback_query(F.data.startswith("stats:player:"))
async def show_player_stats(callback: CallbackQuery, state: FSMContext):
    pid = callback.data.split(":", 2)[2]
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)
    p = get_player(pid)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return

    history = await sheets.get_player_points_history(uid, pid)
    captain_id = (user or {}).get("captain", "")
    is_captain = pid == captain_id

    total = sum(r.get("points", 0) for r in history)
    lines = [
        f"{'⭐ ' if is_captain else ''}<b>{p['name']}</b> ({p['team']})\n"
        f"💰 {fmt_price(p['price'])} | 🏆 <b>{total} pts total</b>\n"
    ]

    if not history:
        lines.append("No points recorded yet.")
    else:
        for r in history:
            bd = r.get("breakdown") or {}
            mc = r.get("match_cache") or {}
            if mc:
                match_label = (f"{mc.get('home_team','?')} "
                               f"{mc.get('home_score','?')}-{mc.get('away_score','?')} "
                               f"{mc.get('away_team','?')}")
            else:
                match_label = f"Match {r.get('match_id','?')[:8]}"

            pts = r.get("points", 0)
            lines.append(f"\n📅 <b>{match_label}</b>")

            if bd.get("goals", 0):
                lines.append(f"  ⚽ {bd['goals']} goal(s): +{bd.get('goals_pts', 0)} pts")
            if bd.get("assists", 0):
                lines.append(f"  🎯 {bd['assists']} assist(s): +{bd.get('assists_pts', 0)} pts")
            if bd.get("yellow_cards", 0):
                lines.append(f"  🟨 Yellow card: {bd.get('yellow_pts', 0)} pts")
            if bd.get("red_cards", 0):
                lines.append(f"  🟥 Red card: {bd.get('red_pts', 0)} pts")
            if bd.get("clean_sheet"):
                lines.append(f"  🧱 Clean sheet: +{bd.get('cs_pts', 0)} pts")
            if bd.get("captain_multiplier", 1) > 1:
                lines.append(f"  ⭐ Captain ×2")
            lines.append(f"  → <b>{pts} pts</b>")

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Back to Stats", callback_data="home:stats")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await callback.answer()


# ── Match Results ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:results")
async def show_results(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    matches = await sheets.get_recent_matches(days=2)

    kb = InlineKeyboardBuilder()

    if not matches:
        kb.button(text=t(lang, "back_home"), callback_data="home:back")
        await callback.message.edit_text(
            "🏟 <b>Recent Results</b>\n\nNo matches found in the last 2 days.\n\n"
            "<i>Results appear here after matches finish.</i>",
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
        await callback.answer()
        return

    lines = ["🏟 <b>Recent UCL Results</b>\n<i>Tap a match for details</i>\n"]
    for m in matches:
        status_emoji = "✅" if m["status"] == "final" else "🔴" if m["status"] == "in_progress" else "⏳"
        date_short = str(m.get("match_date", ""))[-5:]  # MM-DD
        btn_label = (f"{status_emoji} {m['home_team']} "
                     f"{m['home_score']}-{m['away_score']} "
                     f"{m['away_team']} ({date_short})")
        kb.button(text=btn_label, callback_data=f"result:{m['match_id']}")

    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await state.set_state(Stats.results)
    await callback.answer()


@router.callback_query(F.data.startswith("result:"))
async def show_match_detail(callback: CallbackQuery, state: FSMContext):
    match_id = callback.data.split(":", 1)[1]
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    m = await sheets.get_cached_match(match_id)
    if not m:
        await callback.answer("Match not found.", show_alert=True)
        return

    import json
    events = m.get("events") or []
    if isinstance(events, str):
        try:
            events = json.loads(events)
        except Exception:
            events = []

    status_word = {"final": "Full Time", "in_progress": "Live", "scheduled": "Upcoming"}.get(
        m.get("status", ""), m.get("status", "")
    )

    lines = [
        f"⚽ <b>{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}</b>",
        f"📅 {m.get('match_date', '')} | {status_word}\n",
    ]

    goals = [e for e in events if e.get("type") == "goal"]
    yellows = [e for e in events if e.get("type") == "yellow_card"]
    reds = [e for e in events if e.get("type") == "red_card"]

    if goals:
        lines.append("⚽ <b>Goals:</b>")
        for g in goals:
            assist_str = f" (assist: {g['assist']})" if g.get("assist") else ""
            team_str = m["home_team"] if g.get("team") == "home" else m["away_team"]
            lines.append(f"  {g.get('minute', '?')}' {g.get('player', '?')} — {team_str}{assist_str}")

    if yellows:
        lines.append("\n🟨 <b>Yellow cards:</b>")
        for y in yellows:
            lines.append(f"  {y.get('minute', '?')}' {y.get('player', '?')}")

    if reds:
        lines.append("\n🟥 <b>Red cards:</b>")
        for r in reds:
            lines.append(f"  {r.get('minute', '?')}' {r.get('player', '?')}")

    if not goals and not yellows and not reds:
        lines.append("<i>No events recorded yet.</i>")

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Back to Results", callback_data="home:results")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    try:
        await callback.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()
