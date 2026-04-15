import math
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from translations import t
from players import get_by_position, fmt_price, get_player

PLAYERS_PER_PAGE = 8


def lang_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇬🇧 English",  callback_data="lang:en")
    kb.button(text="🇮🇹 Italiano", callback_data="lang:it")
    kb.button(text="🇫🇷 Français", callback_data="lang:fr")
    kb.button(text="🇪🇸 Español",  callback_data="lang:es")
    kb.adjust(2)
    return kb.as_markup()


def rules_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "accept_btn"), callback_data="rules:accept")
    return kb.as_markup()


def home_keyboard(lang: str, user_id: int, squad_submitted: bool,
                  formation_set: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if not formation_set:
        kb.button(text="⚽ " + t(lang, "choose_formation"), callback_data="home:formation")
    else:
        kb.button(text=t(lang, "my_squad_btn"),    callback_data="home:squad")
        kb.button(text=t(lang, "transfers_btn"),   callback_data="home:transfers")
    kb.button(text=t(lang, "leaderboard_btn"), callback_data="home:leaderboard")
    if user_id == config.ADMIN_ID:
        kb.button(text=t(lang, "admin_btn"), callback_data="home:admin")
    kb.adjust(1)
    return kb.as_markup()


def formation_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in config.FORMATIONS:
        kb.button(text=f"⚽ {f}", callback_data=f"formation:{f}")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(3)
    return kb.as_markup()


def _safe_player_name(pid: str, fallback: str = "?") -> str:
    """Return player name or fallback — never crashes on None."""
    p = get_player(pid) if pid else None
    return p["name"] if p else fallback


def squad_keyboard(lang: str, formation: str, squad: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    try:
        parts = formation.split("-")
        n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        n_def, n_mid, n_fwd = 4, 3, 3

    # GK
    gk = squad.get("gk1")
    label = f"🧤 {_safe_player_name(gk)}" if gk else "➕ GK"
    kb.button(text=label, callback_data="slot:gk:gk1")

    # DEF
    for i in range(1, n_def + 1):
        key = f"def{i}"
        p = squad.get(key)
        label = f"🔵 {_safe_player_name(p)}" if p else f"➕ DEF {i}"
        kb.button(text=label, callback_data=f"slot:DEF:{key}")

    # MF
    for i in range(1, n_mid + 1):
        key = f"mf{i}"
        p = squad.get(key)
        label = f"🟡 {_safe_player_name(p)}" if p else f"➕ MF {i}"
        kb.button(text=label, callback_data=f"slot:MF:{key}")

    # FW
    for i in range(1, n_fwd + 1):
        key = f"fw{i}"
        p = squad.get(key)
        label = f"🔴 {_safe_player_name(p)}" if p else f"➕ FW {i}"
        kb.button(text=label, callback_data=f"slot:FW:{key}")

    # Subs — show position picker (ANY)
    for i in range(1, 5):
        key = f"sub{i}"
        p = squad.get(key)
        label = f"🟢 {_safe_player_name(p)}" if p else f"➕ SUB {i}"
        kb.button(text=label, callback_data=f"slot:ANY:{key}")

    # Actions
    filled = _count_filled(squad, formation)
    if filled >= 15:
        cap = squad.get("captain")
        cap_label = f"⭐ Captain: {_safe_player_name(cap)}" if cap else "⭐ Set Captain"
        kb.button(text=cap_label, callback_data="squad:captain")
        kb.button(text="🚀 Submit Squad", callback_data="squad:submit")

    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def _count_filled(squad: dict, formation: str) -> int:
    try:
        parts = formation.split("-")
        n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        n_def, n_mid, n_fwd = 4, 3, 3
    slots = (
        ["gk1"]
        + [f"def{i}" for i in range(1, n_def + 1)]
        + [f"mf{i}"  for i in range(1, n_mid + 1)]
        + [f"fw{i}"  for i in range(1, n_fwd + 1)]
        + [f"sub{i}" for i in range(1, 5)]
    )
    return sum(1 for s in slots if squad.get(s))


def player_list_keyboard(lang: str, position: str, slot: str,
                         page: int, squad: dict) -> InlineKeyboardMarkup:
    all_players = get_by_position(position)
    # Exclude already-picked players (filter out formation strings like "4-3-3")
    taken = {v for v in squad.values() if isinstance(v, str) and not v.startswith("4-") and "-" not in v}
    available = [p for p in all_players if p["id"] not in taken]

    total_pages = max(1, math.ceil(len(available) / PLAYERS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    chunk = available[page * PLAYERS_PER_PAGE: (page + 1) * PLAYERS_PER_PAGE]

    kb = InlineKeyboardBuilder()
    for p in chunk:
        label = f"{p['nation']} {p['name']} ({p['team']}) — {fmt_price(p['price'])}"
        kb.button(text=label, callback_data=f"pick:{p['id']}:{slot}")

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️ Prev", callback_data=f"page:{position}:{slot}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next ▶️", callback_data=f"page:{position}:{slot}:{page + 1}"))
    if nav:
        kb.row(*nav)

    kb.button(text=t(lang, "back_home"), callback_data="squad:view")
    kb.adjust(1)
    return kb.as_markup()


def slot_action_keyboard(lang: str, position: str, slot: str, player_id: str) -> InlineKeyboardMarkup:
    """Shown when user taps a slot that already has a player — Replace or Remove."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Replace player",    callback_data=f"slot_replace:{position}:{slot}")
    kb.button(text="❌ Remove player",     callback_data=f"slot_remove:{slot}")
    kb.button(text="◀️ Back to squad",    callback_data="squad:view")
    kb.adjust(1)
    return kb.as_markup()


def confirm_player_keyboard(lang: str, player_id: str, slot: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "yes_btn"), callback_data=f"confirm_player:{player_id}:{slot}")
    kb.button(text=t(lang, "no_btn"),  callback_data="squad:view")
    kb.adjust(2)
    return kb.as_markup()


def captain_keyboard(lang: str, squad: dict, formation: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    try:
        parts = formation.split("-")
        n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        n_def, n_mid, n_fwd = 4, 3, 3
    starters = (
        ["gk1"]
        + [f"def{i}" for i in range(1, n_def + 1)]
        + [f"mf{i}"  for i in range(1, n_mid + 1)]
        + [f"fw{i}"  for i in range(1, n_fwd + 1)]
    )
    for slot in starters:
        pid = squad.get(slot)
        if pid:
            p = get_player(pid)
            if p:
                kb.button(text=f"⭐ {p['name']} ({p['team']})",
                          callback_data=f"captain:{pid}")
    kb.button(text="◀️ Back to Squad", callback_data="squad:view")
    kb.adjust(1)
    return kb.as_markup()


def confirm_submit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Yes, submit!",  callback_data="submit:confirm")
    kb.button(text=t(lang, "no_btn"),  callback_data="squad:view")
    kb.adjust(2)
    return kb.as_markup()


def transfer_squad_keyboard(lang: str, squad: dict, formation: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    try:
        parts = formation.split("-")
        n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        n_def, n_mid, n_fwd = 4, 3, 3
    all_slots = (
        ["gk1"]
        + [f"def{i}" for i in range(1, n_def + 1)]
        + [f"mf{i}"  for i in range(1, n_mid + 1)]
        + [f"fw{i}"  for i in range(1, n_fwd + 1)]
        + [f"sub{i}" for i in range(1, 5)]
    )
    for slot in all_slots:
        pid = squad.get(slot)
        if pid:
            p = get_player(pid)
            if p:
                kb.button(
                    text=f"❌ {p['name']} ({p['team']}) {fmt_price(p['price'])}",
                    callback_data=f"transfer_out:{pid}:{slot}"
                )
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def confirm_transfer_keyboard(lang: str, pid_out: str, pid_in: str,
                               slot: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Confirm transfer",
              callback_data=f"transfer_confirm:{pid_out}:{pid_in}:{slot}")
    kb.button(text=t(lang, "no_btn"), callback_data="home:transfers")
    kb.adjust(2)
    return kb.as_markup()


def admin_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "admin_send_msg"),  callback_data="admin:send_msg")
    kb.button(text=t(lang, "admin_broadcast"), callback_data="admin:broadcast")
    kb.button(text=t(lang, "admin_pending"),   callback_data="admin:pending")
    kb.button(text="🔄 Reset",                 callback_data="admin:reset")
    kb.button(text=t(lang, "back_home"),       callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()


def reset_type_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Reset user(s) by ID",    callback_data="reset:by_id")
    kb.button(text="🔴 Full campaign reset",     callback_data="reset:campaign")
    kb.button(text="◀️ Back",                   callback_data="admin:back_menu")
    kb.adjust(1)
    return kb.as_markup()


def reset_campaign_confirm_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔴 YES, RESET EVERYTHING",  callback_data="reset:campaign_confirm")
    kb.button(text="❌ Cancel",                  callback_data="admin:back_menu")
    kb.adjust(1)
    return kb.as_markup()


def admin_confirm_send_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Yes, send", callback_data="admin:confirm_yes")
    kb.button(text="❌ Cancel",    callback_data="admin:cancel")
    kb.adjust(2)
    return kb.as_markup()


def admin_broadcast_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 All users",       callback_data="broadcast:all")
    kb.button(text="📋 Specific IDs",    callback_data="broadcast:ids")
    kb.button(text=t(lang, "back_home"), callback_data="home:back")
    kb.adjust(1)
    return kb.as_markup()
