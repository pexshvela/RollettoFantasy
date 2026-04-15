"""
points_calculator.py — Convert match stats into fantasy points.

Points system:
  Goal (FW/MF):     +5
  Goal (DEF/GK):   +10
  Assist:           +3
  Clean sheet (GK/DEF, played ≥60 min): +4
  Yellow card:      -1
  Red card:         -3
  Penalty miss:     -2
  Captain:          ×2 (doubles ALL points, including negative)
"""
import logging
from players import get_player

logger = logging.getLogger(__name__)

POINTS = {
    "goal_fw_mf":         5,
    "goal_def_gk":       10,
    "assist":             3,
    "clean_sheet_gk_def": 4,
    "yellow_card":       -1,
    "red_card":          -3,
    "penalty_miss":      -2,
}


def calc_player_points(player_id: str, stats: dict) -> int:
    """
    Calculate fantasy points for one player based on their match stats.
    stats keys: goals, assists, yellow_cards, red_cards, penalty_miss,
                minutes_played, goals_conceded, clean_sheet (bool)
    """
    if not stats:
        return 0

    p = get_player(player_id)
    if not p:
        logger.warning("Unknown player_id: %s", player_id)
        return 0

    position = p.get("position", "FW")
    pts = 0

    goals = int(stats.get("goals") or 0)
    if goals > 0:
        rate = POINTS["goal_def_gk"] if position in ("GK", "DEF") else POINTS["goal_fw_mf"]
        pts += goals * rate

    pts += int(stats.get("assists") or 0) * POINTS["assist"]
    pts += int(stats.get("yellow_cards") or 0) * POINTS["yellow_card"]
    pts += int(stats.get("red_cards") or 0) * POINTS["red_card"]
    pts += int(stats.get("penalty_miss") or 0) * POINTS["penalty_miss"]

    # Clean sheet: GK or DEF who played ≥60 minutes and team conceded 0
    if position in ("GK", "DEF"):
        minutes = int(stats.get("minutes_played") or 90)
        conceded = int(stats.get("goals_conceded") or 0)
        clean = stats.get("clean_sheet", conceded == 0)
        if clean and minutes >= 60:
            pts += POINTS["clean_sheet_gk_def"]

    logger.debug("Player %s (%s) pts=%d stats=%s", p["name"], position, pts, stats)
    return pts


def calc_squad_points(squad: dict, player_stats: dict[str, dict]) -> dict[str, int]:
    """
    Calculate points for every player in a squad.
    squad: {slot: player_id, ...}
    player_stats: {player_id: stats_dict, ...}
    Returns: {player_id: points}
    """
    results = {}
    captain_id = squad.get("captain", "")

    all_slots = (
        ["gk1"]
        + [f"def{i}" for i in range(1, 6)]
        + [f"mf{i}"  for i in range(1, 6)]
        + [f"fw{i}"  for i in range(1, 4)]
        + [f"sub{i}" for i in range(1, 5)]
    )

    for slot in all_slots:
        pid = squad.get(slot)
        if not pid:
            continue
        stats = player_stats.get(pid)
        if stats is None:
            # Player didn't play / no data — 0 points
            results[pid] = 0
            continue
        pts = calc_player_points(pid, stats)
        # Captain doubles total
        if pid == captain_id:
            pts *= 2
        results[pid] = pts

    return results


def total_squad_points(squad: dict, player_stats: dict[str, dict]) -> int:
    """Sum of points for all 11 starters (not subs)."""
    captain_id = squad.get("captain", "")

    try:
        formation = squad.get("formation", "4-3-3") or "4-3-3"
        parts = formation.split("-")
        n_def, n_mid, n_fwd = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        n_def, n_mid, n_fwd = 4, 3, 3

    starter_slots = (
        ["gk1"]
        + [f"def{i}" for i in range(1, n_def + 1)]
        + [f"mf{i}"  for i in range(1, n_mid + 1)]
        + [f"fw{i}"  for i in range(1, n_fwd + 1)]
    )

    total = 0
    for slot in starter_slots:
        pid = squad.get(slot)
        if not pid:
            continue
        stats = player_stats.get(pid)
        if stats is None:
            continue
        pts = calc_player_points(pid, stats)
        if pid == captain_id:
            pts *= 2
        total += pts

    return total
