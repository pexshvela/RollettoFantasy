"""helpers.py — Shared utility functions."""
import logging
from typing import Optional
import sheets
import players as pl_module
from translations import t
from players import fmt_price, mask_username

logger = logging.getLogger(__name__)

FORMATIONS = {
    "4-3-3": {"DEF": 4, "MF": 3, "FW": 3},
    "4-4-2": {"DEF": 4, "MF": 4, "FW": 2},
    "3-4-3": {"DEF": 3, "MF": 4, "FW": 3},
    "3-5-2": {"DEF": 3, "MF": 5, "FW": 2},
    "5-3-2": {"DEF": 5, "MF": 3, "FW": 2},
    "4-5-1": {"DEF": 4, "MF": 5, "FW": 1},
}

POS_EMOJI = {"GK": "🧤", "DEF": "🔵", "MF": "🟡", "FW": "🔴"}
POS_NAME  = {"GK": "Goalkeeper", "DEF": "Defender", "MF": "Midfielder", "FW": "Forward"}


async def get_lang(telegram_id: int, user: dict = None) -> str:
    if user is None:
        user = await sheets.get_user(telegram_id)
    return (user or {}).get("language", "en")


def get_formation_slots(formation: str) -> dict[str, int]:
    return FORMATIONS.get(formation, FORMATIONS["4-3-3"])


def get_starter_slots(formation: str) -> list[str]:
    """Return ordered list of starter slot names for a formation."""
    slots_def = get_formation_slots(formation)
    slots = ["gk1"]
    for i in range(1, slots_def["DEF"] + 1): slots.append(f"def{i}")
    for i in range(1, slots_def["MF"] + 1):  slots.append(f"mf{i}")
    for i in range(1, slots_def["FW"] + 1):  slots.append(f"fw{i}")
    return slots


def get_bench_slots() -> list[str]:
    return ["bench_gk", "bench_def", "bench_mf", "bench_fw"]


def get_all_slots(formation: str) -> list[str]:
    return get_starter_slots(formation) + get_bench_slots()


def slot_to_position(slot: str) -> str:
    """Convert slot name to position: gk1→GK, def3→DEF etc."""
    if slot.startswith("gk") or slot == "bench_gk":    return "GK"
    if slot.startswith("def") or slot == "bench_def":  return "DEF"
    if slot.startswith("mf") or slot == "bench_mf":    return "MF"
    if slot.startswith("fw") or slot == "bench_fw":    return "FW"
    return "FW"


def build_squad_visual(squad: dict, formation: str, captain_id: str = "",
                        points_summary: dict = None) -> str:
    """Build text representation of squad for display."""
    if not squad:
        return "No squad yet."

    lines = []
    starter_slots = get_starter_slots(formation)
    bench_slots   = get_bench_slots()

    def player_line(slot: str) -> str:
        pid = squad.get(slot, "")
        if not pid:
            pos = slot_to_position(slot)
            return f"{POS_EMOJI.get(pos,'⚪')} <i>Empty</i>"
        p = pl_module.get_player(pid)
        if not p:
            return f"⚪ Unknown"
        cap  = " ⭐" if pid == captain_id else ""
        pts  = f" ({points_summary[pid]}pts)" if points_summary and pid in points_summary else ""
        return f"{POS_EMOJI.get(p['position'],'⚪')} {p['name']}{cap}{pts} — {fmt_price(p['price'])}"

    lines.append(f"<b>Formation: {formation}</b>")
    lines.append("")

    # Starters
    lines.append("<b>Starting XI:</b>")
    for slot in starter_slots:
        lines.append(player_line(slot))

    lines.append("")
    lines.append("<b>Bench:</b>")
    for slot in bench_slots:
        lines.append(player_line(slot))

    return "\n".join(lines)


def calc_squad_cost(squad: dict) -> int:
    total = 0
    for pid in squad.values():
        if isinstance(pid, str) and pid:
            p = pl_module.get_player(pid)
            if p:
                total += p["price"]
    return total


def squad_is_complete(squad: dict, formation: str) -> bool:
    all_slots = get_all_slots(formation)
    return all(squad.get(s) for s in all_slots)
