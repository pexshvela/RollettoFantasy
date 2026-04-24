"""inline.py — All inline keyboards."""
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from translations import t
from helpers import FORMATIONS


def home_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_squad"),       callback_data="home:squad")
    kb.button(text=t(lang, "btn_transfers"),   callback_data="home:transfers")
    kb.button(text=t(lang, "btn_confirm"),     callback_data="home:confirm")
    kb.button(text=t(lang, "btn_stats"),       callback_data="home:stats")
    kb.button(text=t(lang, "btn_results"),     callback_data="home:results")
    kb.button(text=t(lang, "btn_leaderboard"), callback_data="home:leaderboard")
    kb.button(text=t(lang, "btn_rules"),       callback_data="home:rules")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def back_home(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    return kb.as_markup()


def back_home_row(lang: str, kb: InlineKeyboardBuilder) -> InlineKeyboardBuilder:
    """Add home button to existing keyboard builder."""
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    return kb


def formation_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in FORMATIONS:
        kb.button(text=f"⚽ {f}", callback_data=f"formation:{f}")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def player_list_keyboard(players: list, position: str,
                          lang: str, page: int = 0,
                          page_size: int = 8) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * page_size
    end   = start + page_size
    page_players = players[start:end]

    for p in page_players:
        from players import fmt_price
        label = f"{p['name']} ({p['team']}) — {fmt_price(p['price'])}"
        kb.button(text=label, callback_data=f"pick:{position}:{p['id']}")

    # Pagination
    nav = []
    if page > 0:
        nav.append(("◀️ Prev", f"page:{position}:{page-1}"))
    if end < len(players):
        nav.append(("Next ▶️", f"page:{position}:{page+1}"))
    for label, cb in nav:
        kb.button(text=label, callback_data=cb)

    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def captain_keyboard(squad: dict, formation: str, lang: str) -> InlineKeyboardMarkup:
    from helpers import get_starter_slots
    from players import get_player, fmt_price
    kb = InlineKeyboardBuilder()
    for slot in get_starter_slots(formation):
        pid = squad.get(slot)
        if not pid:
            continue
        p = get_player(pid)
        if not p:
            continue
        kb.button(text=f"⭐ {p['name']} ({p['team']})",
                  callback_data=f"captain:{pid}")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def squad_review_keyboard(lang: str, confirmed: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if not confirmed:
        kb.button(text="✅ Confirm Squad",   callback_data="squad:confirm")
        kb.button(text="🔄 Change Player",   callback_data="squad:change")
    else:
        kb.button(text="🔄 Change Player",   callback_data="squad:change")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def transfer_pick_out_keyboard(squad: dict, formation: str, lang: str) -> InlineKeyboardMarkup:
    from helpers import get_all_slots
    from players import get_player, fmt_price
    kb = InlineKeyboardBuilder()
    for slot in get_all_slots(formation):
        pid = squad.get(slot)
        if not pid:
            continue
        p = get_player(pid)
        if not p:
            continue
        kb.button(text=f"❌ {p['name']} — {fmt_price(p['price'])}",
                  callback_data=f"transfer:out:{pid}:{slot}")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def leaderboard_keyboard(lang: str, gw_id: int = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "lb_btn_overall"), callback_data="lb:overall")
    if gw_id:
        kb.button(text=t(lang, "lb_btn_gw"), callback_data=f"lb:gw:{gw_id}")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(2, 1)
    return kb.as_markup()


def results_keyboard(matches: list, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for m in matches:
        label = (f"{'✅' if m['status']=='final' else '🔴' if m['status']=='in_progress' else '⏳'}"
                 f" {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']}"
                 f" ({str(m.get('match_date',''))[-5:]})")
        kb.button(text=label, callback_data=f"result:{m['match_id']}")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def stats_players_keyboard(squad: dict, formation: str, lang: str,
                            points_summary: dict) -> InlineKeyboardMarkup:
    from helpers import get_starter_slots
    from players import get_player
    kb = InlineKeyboardBuilder()
    for slot in get_starter_slots(formation):
        pid = squad.get(slot)
        if not pid:
            continue
        p = get_player(pid)
        if not p:
            continue
        pts = points_summary.get(pid, 0)
        kb.button(text=f"{p['name']} — {pts} pts",
                  callback_data=f"stats:player:{pid}")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def admin_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📨 Message User",  callback_data="admin:msg_user")
    kb.button(text="📢 Broadcast",     callback_data="admin:broadcast")
    kb.button(text="🔄 Reset User",    callback_data="admin:reset_user")
    kb.button(text="💣 Full Reset",    callback_data="admin:reset_all")
    kb.button(text="📖 Commands",      callback_data="admin:commands")
    kb.button(text="🏠 Home",          callback_data="home:back")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()
