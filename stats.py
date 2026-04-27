"""stats.py — My Stats and Match Results views."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import sheets
from players import get_player, fmt_price, mask_username
from states import Stats, Results
from translations import t
from helpers import get_lang, get_starter_slots, POS_EMOJI
from inline import home_keyboard, results_keyboard, stats_players_keyboard

logger = logging.getLogger(__name__)
router = Router()


# ── My Stats ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:stats")
async def show_stats(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    pts_summary = await sheets.get_squad_points_summary(uid)
    total       = sum(pts_summary.values())
    squad       = await sheets.get_squad(uid)
    formation   = user.get("formation", "4-3-3") if user else "4-3-3"
    captain_id  = (user or {}).get("captain", "")

    if not squad:
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "back_home"), callback_data="home:back")
        await callback.message.edit_text(
            t(lang, "stats_title", total=total) + t(lang, "no_stats"),
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
        await callback.answer()
        return

    lines = [t(lang, "stats_title", total=total)]
    for slot in get_starter_slots(formation):
        pid = squad.get(slot)
        if not pid: continue
        p   = get_player(pid)
        if not p:   continue
        pts = pts_summary.get(pid, 0)
        cap = " ⭐" if pid == captain_id else ""
        lines.append(f"{POS_EMOJI.get(p['position'],'⚪')} {p['name']}{cap} — <b>{pts} pts</b>")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=stats_players_keyboard(squad, formation, lang, pts_summary)
    )
    await state.set_state(Stats.viewing)
    await callback.answer()


@router.callback_query(F.data.startswith("stats:player:"))
async def show_player_stats(callback: CallbackQuery, state: FSMContext):
    pid  = callback.data.split(":", 2)[2]
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    p = get_player(pid)
    if not p:
        await callback.answer("Player not found.", show_alert=True)
        return

    history = await sheets.get_player_points_history(uid, pid)
    total   = sum(r.get("points", 0) for r in history)
    cap     = pid == (user or {}).get("captain", "")

    lines = [
        t(lang, "player_detail",
          name=p["name"], team=p["team"],
          price=fmt_price(p["price"]), total=total),
    ]

    if not history:
        lines.append("No match points yet.")
    else:
        for r in history:
            bd = r.get("breakdown") or {}
            match_label = bd.get("match", f"Match {r.get('match_id','?')[:8]}")
            pts = r.get("points", 0)
            lines.append(f"\n📅 <b>{match_label}</b>")

            def add(label, val, pts_val):
                if val:
                    sign = "+" if pts_val >= 0 else ""
                    lines.append(f"  {label}: {sign}{pts_val} pts")

            add("🕐 Played",        bd.get("pts_appearance", 0), bd.get("pts_appearance", 0))
            add("⚽ Goals",          bd.get("goals", 0),         bd.get("pts_goals", 0))
            add("🎯 Assists",        bd.get("assists", 0),       bd.get("pts_assists", 0))
            add("🧱 Clean sheet",    bd.get("clean_sheet"),      bd.get("pts_clean_sheet", 0))
            add("🧤 Saves /3",       bd.get("saves", 0),         bd.get("pts_saves", 0))
            add("🛑 Pen saved",      bd.get("penalty_saved", 0), bd.get("pts_pen_saved", 0))
            add("📉 Conceded /2",    bd.get("goals_conceded", 0),bd.get("pts_conceded", 0))
            add("🎯 Pen earned",     bd.get("penalty_earned", 0),bd.get("pts_pen_earned", 0))
            add("❌ Pen missed",     bd.get("penalty_miss", 0),  bd.get("pts_pen_miss", 0))
            add("🟨 Yellow",         bd.get("yellow_cards", 0),  bd.get("pts_yellow", 0))
            add("🟥 Red",            bd.get("red_cards", 0),     bd.get("pts_red", 0))
            add("😬 Own goal",       bd.get("own_goals", 0),     bd.get("pts_own_goals", 0))
            add("🛡 Def acts /3",    bd.get("def_actions", 0),   bd.get("pts_def_actions", 0))
            if bd.get("captain"):
                lines.append(f"  ⭐ Captain ×2 (base: {bd.get('base_pts',0)} pts)")
            lines.append(f"  → <b>{pts} pts</b>")

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Back to Stats", callback_data="home:stats")
    kb.button(text=t(lang, "back_home"),   callback_data="home:back")
    kb.adjust(1)

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await callback.answer()


# ── Results ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:results")
async def show_results(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    matches = await sheets.get_recent_matches(days=14)
    # Show finished or in-progress matches
    matches = [m for m in matches if m.get("status") in (
        "final", "in_progress", "FT", "AET", "PEN", "finished",
        "Match Finished", "1H", "2H", "HT", "ET", "BT", "P", "LIVE"
    )]

    if not matches:
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "back_home"), callback_data="home:back")
        await callback.message.edit_text(
            t(lang, "results_title") + "\n\n" + t(lang, "no_results"),
            parse_mode="HTML", reply_markup=kb.as_markup()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        t(lang, "results_title") + "\n\n<i>Tap a match for details</i>",
        parse_mode="HTML",
        reply_markup=results_keyboard(matches, lang)
    )
    await state.set_state(Results.viewing)
    await callback.answer()


@router.callback_query(F.data.startswith("result:"))
async def show_match_detail(callback: CallbackQuery, state: FSMContext):
    match_id = callback.data.split(":", 1)[1]
    uid      = callback.from_user.id
    user     = await sheets.get_user(uid)
    lang     = await get_lang(uid, user)

    m = await sheets.get_cached_match(match_id)
    if not m:
        await callback.answer("Match not found.", show_alert=True)
        return

    events   = m.get("events") or []
    status_w = {"final":"Full Time","in_progress":"Live","scheduled":"Upcoming"}.get(
        m.get("status",""), m.get("status",""))

    lines = [
        f"⚽ <b>{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}</b>",
        f"📅 {m.get('match_date','')} {m.get('match_time','')} | {status_w}",
        f"🏆 {m.get('tournament','')} — {m.get('round','')}",
        "",
    ]

    goals   = [e for e in events if e.get("type") == "goal"]
    yellows = [e for e in events if e.get("type") == "yellow_card"]
    reds    = [e for e in events if e.get("type") in ("red_card","yellow_then_red")]
    own     = [e for e in events if e.get("type") == "own_goal"]

    if goals:
        lines.append("⚽ <b>Goals:</b>")
        for g in goals:
            assist = f" (assist: {g['assist']})" if g.get("assist") else ""
            lines.append(f"  {g.get('minute','')}' {g.get('player','')} — {g.get('team','')}{assist}")

    if own:
        lines.append("\n🤦 <b>Own Goals:</b>")
        for g in own:
            lines.append(f"  {g.get('minute','')}' {g.get('player','')} — {g.get('team','')}")

    if yellows:
        lines.append("\n🟨 <b>Yellow Cards:</b>")
        for y in yellows:
            lines.append(f"  {y.get('minute','')}' {y.get('player','')} — {y.get('team','')}")

    if reds:
        lines.append("\n🟥 <b>Red Cards:</b>")
        for r in reds:
            lines.append(f"  {r.get('minute','')}' {r.get('player','')} — {r.get('team','')}")

    if not goals and not yellows and not reds and not own:
        lines.append("<i>No events recorded yet.</i>")

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Back to Results", callback_data="home:results")
    kb.button(text=t(lang, "back_home"),    callback_data="home:back")
    kb.adjust(1)

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await callback.answer()


# ── Leaderboard ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home:leaderboard")
async def show_leaderboard(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    gw = await sheets.get_active_gameweek()

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "lb_btn_overall"), callback_data="lb:overall")
    if gw:
        kb.button(text=t(lang, "lb_btn_gw"), callback_data=f"lb:gw:{gw['id']}")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(2, 1)

    await callback.message.edit_text(
        "🏆 <b>Leaderboard</b>\n\nChoose view:",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "lb:overall")
async def show_overall_lb(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    user = await sheets.get_user(uid)
    lang = await get_lang(uid, user)

    rows = await sheets.get_overall_leaderboard(20)
    my_uid = uid

    lines = [t(lang, "lb_overall"), ""]
    for i, r in enumerate(rows, 1):
        username = mask_username(r.get("username", "?"))
        pts      = r.get("total_points", 0)
        me       = " 👈" if r.get("telegram_id") == my_uid else ""
        lines.append(t(lang, "lb_entry", rank=i, username=username, pts=pts) + me)

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back_home"), callback_data="home:back")

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lb:gw:"))
async def show_gw_lb(callback: CallbackQuery, state: FSMContext):
    gw_id = int(callback.data.split(":")[2])
    uid   = callback.from_user.id
    user  = await sheets.get_user(uid)
    lang  = await get_lang(uid, user)

    rows = await sheets.get_gameweek_leaderboard(gw_id, 20)
    gw   = await sheets.get_gameweek(gw_id)
    gw_name = gw["name"] if gw else str(gw_id)

    lines = [t(lang, "lb_gameweek", n=gw_name), ""]
    for i, r in enumerate(rows, 1):
        username = mask_username(r.get("username", "?"))
        pts      = r.get("total_points", 0)
        me       = " 👈" if r.get("telegram_id") == uid else ""
        lines.append(t(lang, "lb_entry", rank=i, username=username, pts=pts) + me)

    kb = InlineKeyboardBuilder()
    kb.button(text="🏆 Overall",     callback_data="lb:overall")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(2)

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup()
    )
    await callback.answer()
