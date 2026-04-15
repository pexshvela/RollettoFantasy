import config
from players import get_player, fmt_price


async def get_lang(telegram_id: int, user: dict | None) -> str:
    """Return user's language or default to English."""
    if user:
        return user.get("language", "en") or "en"
    return "en"


def build_home_text(lang: str, user: dict | None, squad: dict | None) -> str:
    from translations import t
    budget = int(user.get("budget_remaining", config.TOTAL_BUDGET) if user else config.TOTAL_BUDGET)
    formation = user.get("formation", "") if user else ""
    captain_id = user.get("captain", "") if user else ""
    points = user.get("total_points", 0) if user else 0
    submitted = (user.get("squad_submitted", "no") == "yes") if user else False

    if captain_id:
        cap = get_player(captain_id)
        captain_name = cap["name"] if cap else "N/A"
    else:
        captain_name = "Not set"

    filled = count_squad_filled(squad, formation) if squad and formation else 0

    return t(lang, "home_title",
             budget=fmt_price(budget),
             filled=filled,
             captain=captain_name,
             points=points)


def build_squad_visual(formation: str, squad: dict) -> str:
    """Build a text-based formation visual."""
    if not formation:
        return ""

    parts = formation.split("-")
    n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])

    def slot_label(key: str, emoji: str) -> str:
        pid = squad.get(key)
        if pid:
            p = get_player(pid)
            cap_mark = " ⭐" if squad.get("captain") == pid else ""
            return f"{emoji}{p['name']}{cap_mark}" if p else f"{emoji}?"
        return f"➕"

    lines = []

    # Forwards
    fwd_slots = [slot_label(f"fw{i}", "🔴") for i in range(1, n_fwd + 1)]
    lines.append("  ".join(fwd_slots))

    # Midfielders
    mid_slots = [slot_label(f"mf{i}", "🟡") for i in range(1, n_mid + 1)]
    lines.append("  ".join(mid_slots))

    # Defenders
    def_slots = [slot_label(f"def{i}", "🔵") for i in range(1, n_def + 1)]
    lines.append("  ".join(def_slots))

    # GK
    lines.append(slot_label("gk1", "🧤"))

    # Subs
    sub_slots = []
    for i in range(1, 5):
        pid = squad.get(f"sub{i}")
        if pid:
            p = get_player(pid)
            sub_slots.append(p["name"] if p else "?")
        else:
            sub_slots.append("Empty")
    lines.append("📋 Subs: " + " | ".join(sub_slots))

    return "\n\n".join(lines)


def count_squad_filled(squad: dict | None, formation: str) -> int:
    if not squad or not formation:
        return 0
    parts = formation.split("-")
    n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])
    slots = (
        ["gk1"]
        + [f"def{i}" for i in range(1, n_def + 1)]
        + [f"mf{i}"  for i in range(1, n_mid + 1)]
        + [f"fw{i}"  for i in range(1, n_fwd + 1)]
        + [f"sub{i}" for i in range(1, 5)]
    )
    return sum(1 for s in slots if squad.get(s))
