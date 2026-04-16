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

            def _line(label, val, pts_val):
                if val and val != 0:
                    sign = "+" if pts_val >= 0 else ""
                    lines.append(f"  {label}: {sign}{pts_val} pts")

            mins = bd.get("minutes_played", 0)
            app  = bd.get("pts_appearance", 0)
            if app:
                mins_label = f"60+ min" if mins >= 60 else f"{mins} min"
                lines.append(f"  🕐 Played ({mins_label}): +{app} pts")
            _line("⚽ Goals",            bd.get("goals"),          bd.get("pts_goals", 0))
            _line("🎯 Assists",          bd.get("assists"),         bd.get("pts_assists", 0))
            _line("🧱 Clean sheet",      bd.get("clean_sheet"),     bd.get("pts_clean_sheet", 0))
            _line("🧤 Saves /3",         bd.get("saves"),           bd.get("pts_saves", 0))
            _line("🛑 Penalty saved",    bd.get("penalty_saved"),   bd.get("pts_pen_saved", 0))
            _line("📉 Goals conceded /2",bd.get("goals_conceded"),  bd.get("pts_conceded", 0))
            _line("🎯 Penalty earned",   bd.get("penalty_earned"),  bd.get("pts_pen_earned", 0))
            _line("❌ Penalty missed",   bd.get("penalty_miss"),    bd.get("pts_pen_miss", 0))
            _line("⚠️ Pen conceded",     bd.get("penalty_conceded"),bd.get("pts_pen_conceded", 0))
            _line("🟨 Yellow card",      bd.get("yellow_cards"),    bd.get("pts_yellow", 0))
            _line("🟥 Red card",         bd.get("red_cards"),       bd.get("pts_red", 0))
            _line("😬 Own goal",         bd.get("own_goals"),       bd.get("pts_own_goals", 0))
            _line("🛡 Def. actions /3",  bd.get("def_actions"),     bd.get("pts_def_actions", 0))
            if bd.get("captain_multiplier", 1) > 1:
                lines.append(f"  ⭐ Captain ×2 (base: {bd.get('base_pts',0)} pts)")
            lines.append(f"  → <b>{pts} pts</b>")

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Back to Stats", callback_data="home:stats")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await callback.answer()


# ── Tournament matching helper ───────────────────────────────────────────────

def _tournament_matches(tournament_name: str, keywords: list) -> bool:
    t = tournament_name.lower()
    for kw in keywords:
        kw_words = kw.lower().replace("-", " ").replace("_", " ")
        if kw.lower() in t or kw_words in t:
            return True
        kw_parts = kw_words.split()
        if len(kw_parts) == 1 and len(kw_parts[0]) > 5 and kw_parts[0] in t:
            return True
    return False


# ── Match Results ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:results")
async def show_results(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    all_matches = await sheets.get_recent_matches(days=2)

    # Filter by active tournament keywords
    keywords = await sheets.get_tournament_keywords()
    if keywords:
        matches = [
            m for m in all_matches
            if _tournament_matches(m.get("tournament") or "", keywords)
        ]
    else:
        matches = all_matches

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

    tournament_label = matches[0].get("tournament") or "Recent Matches"
    lines = [f"🏟 <b>{tournament_label}</b>\n<i>Tap a match for details</i>\n"]
    for m in matches:
        status_emoji = "✅" if m["status"] == "final" else "🔴" if m["status"] == "in_progress" else "⏳"
        date_short = str(m.get("match_date", ""))[-5:]
        btn_label = (f"{status_emoji} {m['home_team']} "
                     f"{m['home_score']}-{m['away_score']} "
                     f"{m['away_team']} ({date_short})")
        kb.button(text=btn_label, callback_data=f"result:{m['match_id']}")


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
