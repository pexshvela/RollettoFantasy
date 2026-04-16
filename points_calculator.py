"""
points_calculator.py — Fantasy points based on official rules.

All positions:
  Played (any):        +1
  Played 60+ min:      +1  (cumulative, so 60+ min = +2 total)
  Assist:              +3
  Penalty earned:      +2
  Penalty conceded:    -1
  Penalty missed:      -2
  Yellow card:         -1
  Red / 2nd yellow:    -3
  Yellow + direct red: -4
  Own goal:            -2
  Defensive actions (tackles+interceptions+blocks ≥3 each group of 3): +1

GK:
  Goal:               +6
  Penalty saved:      +5
  Clean sheet 60+min: +4
  Goals conceded per 2: -1
  Saves per 3:        +1

DEF:
  Goal:               +6
  Clean sheet 60+min: +4
  Goals conceded per 2: -1

MF:
  Goal:               +5
  Clean sheet 60+min: +1

FW:
  Goal:               +4

Captain doubles ALL points (including negative).
"""
import logging
from players import ALL_PLAYERS

logger = logging.getLogger(__name__)


def calc_player_points(player_id: str, stats: dict) -> int:
    if not stats:
        return 0

    p = ALL_PLAYERS.get(player_id)
    if not p:
        return 0

    position = p.get("position", "FW")
    pts = 0
    minutes = int(stats.get("minutes_played") or 0)

    # ── Appearance ────────────────────────────────────────────────────────────
    if minutes > 0:
        pts += 1           # played at all
        if minutes >= 60:
            pts += 1       # 60+ minutes

    # ── Goals ─────────────────────────────────────────────────────────────────
    goals = int(stats.get("goals") or 0)
    goal_pts = {"GK": 6, "DEF": 6, "MF": 5, "FW": 4}.get(position, 4)
    pts += goals * goal_pts

    # ── Assists ───────────────────────────────────────────────────────────────
    pts += int(stats.get("assists") or 0) * 3

    # ── Clean sheet ───────────────────────────────────────────────────────────
    if minutes >= 60 and stats.get("clean_sheet"):
        cs_pts = {"GK": 4, "DEF": 4, "MF": 1, "FW": 0}.get(position, 0)
        pts += cs_pts

    # ── Goals conceded (GK + DEF only, -1 per 2 goals) ───────────────────────
    if position in ("GK", "DEF") and minutes > 0:
        conceded = int(stats.get("goals_conceded") or 0)
        pts -= (conceded // 2)

    # ── GK specific ───────────────────────────────────────────────────────────
    if position == "GK":
        saves = int(stats.get("saves") or 0)
        pts += saves // 3                          # +1 per 3 saves
        pts += int(stats.get("penalty_saved") or 0) * 5

    # ── Defensive actions (+1 per 3 combined tackles/interceptions/blocks) ────
    tackles      = int(stats.get("tackles") or 0)
    interceptions= int(stats.get("interceptions") or 0)
    blocks       = int(stats.get("blocks") or 0)
    defensive_actions = tackles + interceptions + blocks
    pts += defensive_actions // 3

    # ── Cards ─────────────────────────────────────────────────────────────────
    yellow = int(stats.get("yellow_cards") or 0)
    red    = int(stats.get("red_cards") or 0)
    y_and_r= int(stats.get("yellow_then_red") or 0)  # yellow + direct red = -4

    pts += yellow * -1
    pts += red    * -3
    pts += y_and_r * -1   # additional -1 on top of yellow's -1 for direct red combo

    # ── Penalty events ────────────────────────────────────────────────────────
    pts += int(stats.get("penalty_earned") or 0)  * 2
    pts += int(stats.get("penalty_conceded") or 0) * -1
    pts += int(stats.get("penalty_miss") or 0)     * -2

    # ── Own goals ─────────────────────────────────────────────────────────────
    pts += int(stats.get("own_goals") or 0) * -2

    logger.debug("Player %s (%s) = %d pts | stats=%s", p["name"], position, pts, stats)
    return pts


def build_breakdown(player_id: str, stats: dict, is_captain: bool) -> dict:
    """Build human-readable breakdown dict for display in Stats view."""
    p = ALL_PLAYERS.get(player_id)
    if not p:
        return {}

    position = p.get("position", "FW")
    minutes  = int(stats.get("minutes_played") or 0)
    goals    = int(stats.get("goals") or 0)
    assists  = int(stats.get("assists") or 0)
    yellow   = int(stats.get("yellow_cards") or 0)
    red      = int(stats.get("red_cards") or 0)
    saves    = int(stats.get("saves") or 0)
    pen_saved= int(stats.get("penalty_saved") or 0)
    pen_miss = int(stats.get("penalty_miss") or 0)
    pen_earn = int(stats.get("penalty_earned") or 0)
    pen_conc = int(stats.get("penalty_conceded") or 0)
    conceded = int(stats.get("goals_conceded") or 0)
    own_goals= int(stats.get("own_goals") or 0)
    clean    = bool(stats.get("clean_sheet"))
    tackles  = int(stats.get("tackles") or 0)
    ints     = int(stats.get("interceptions") or 0)
    blocks   = int(stats.get("blocks") or 0)
    def_acts = tackles + ints + blocks

    goal_pts = {"GK": 6, "DEF": 6, "MF": 5, "FW": 4}.get(position, 4)
    cs_pts   = {"GK": 4, "DEF": 4, "MF": 1, "FW": 0}.get(position, 0)

    raw_pts = calc_player_points(player_id, stats)
    final   = raw_pts * 2 if is_captain else raw_pts

    return {
        # raw numbers
        "minutes_played":  minutes,
        "goals":           goals,
        "assists":         assists,
        "yellow_cards":    yellow,
        "red_cards":       red,
        "saves":           saves,
        "penalty_saved":   pen_saved,
        "penalty_miss":    pen_miss,
        "penalty_earned":  pen_earn,
        "penalty_conceded":pen_conc,
        "goals_conceded":  conceded,
        "own_goals":       own_goals,
        "clean_sheet":     clean,
        "def_actions":     def_acts,
        # points breakdown
        "pts_appearance":  (1 if minutes > 0 else 0) + (1 if minutes >= 60 else 0),
        "pts_goals":       goals * goal_pts,
        "pts_assists":     assists * 3,
        "pts_clean_sheet": cs_pts if (clean and minutes >= 60) else 0,
        "pts_conceded":    -(conceded // 2) if position in ("GK","DEF") else 0,
        "pts_saves":       (saves // 3) if position == "GK" else 0,
        "pts_pen_saved":   pen_saved * 5,
        "pts_pen_miss":    pen_miss * -2,
        "pts_pen_earned":  pen_earn * 2,
        "pts_pen_conceded":pen_conc * -1,
        "pts_yellow":      yellow * -1,
        "pts_red":         red * -3,
        "pts_own_goals":   own_goals * -2,
        "pts_def_actions": def_acts // 3,
        "captain_multiplier": 2 if is_captain else 1,
        "base_pts":        raw_pts,
        "total":           final,
    }
