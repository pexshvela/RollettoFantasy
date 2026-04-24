"""
points_calculator.py — Official fantasy points rules.

All players:
  Played any:          +1
  Played 60+ min:      +1
  Assist:              +3
  Penalty earned:      +2
  Penalty conceded:    -1
  Penalty missed:      -2
  Yellow card:         -1
  Red card:            -3
  Yellow + Red:        -4
  Own goal:            -2
  Def actions per 3:   +1  (tackles + interceptions + blocks)

GK:  Goal +6, Pen saved +5, CS(60+) +4, Conceded/2 -1, Saves/3 +1
DEF: Goal +6, CS(60+) +4, Conceded/2 -1
MF:  Goal +5, CS(60+) +1
FW:  Goal +4

Captain: ×2 all points
"""
from players import get_player


def calc_points(player_id: str, stats: dict) -> int:
    """Calculate raw points (before captain multiplier)."""
    p = get_player(player_id)
    if not p:
        return 0

    pos     = p["position"]
    minutes = int(stats.get("minutes_played") or 0)
    pts     = 0

    # Appearance
    if minutes > 0:
        pts += 1
        if minutes >= 60:
            pts += 1

    # Goals
    goals = int(stats.get("goals") or 0)
    goal_pts = {"GK": 6, "DEF": 6, "MF": 5, "FW": 4}.get(pos, 4)
    pts += goals * goal_pts

    # Assists
    pts += int(stats.get("assists") or 0) * 3

    # Clean sheet (60+ min required)
    if minutes >= 60 and stats.get("clean_sheet"):
        cs_pts = {"GK": 4, "DEF": 4, "MF": 1, "FW": 0}.get(pos, 0)
        pts += cs_pts

    # Goals conceded (GK + DEF only, per 2)
    if pos in ("GK", "DEF") and minutes > 0:
        conceded = int(stats.get("goals_conceded") or 0)
        pts -= conceded // 2

    # GK saves per 3
    if pos == "GK":
        saves = int(stats.get("saves") or 0)
        pts += saves // 3
        pts += int(stats.get("penalty_saved") or 0) * 5

    # Defensive actions per 3
    tackles       = int(stats.get("tackles") or 0)
    interceptions = int(stats.get("interceptions") or 0)
    blocks        = int(stats.get("blocks") or 0)
    pts += (tackles + interceptions + blocks) // 3

    # Cards
    yellow      = int(stats.get("yellow_cards") or 0)
    red         = int(stats.get("red_cards") or 0)
    yellow_red  = int(stats.get("yellow_then_red") or 0)

    pts += yellow * -1
    pts += red    * -3
    pts += yellow_red * -1  # extra -1 on top of yellow's -1

    # Penalty events
    pts += int(stats.get("penalty_earned") or 0)   * 2
    pts += int(stats.get("penalty_conceded") or 0)  * -1
    pts += int(stats.get("penalty_miss") or 0)      * -2

    # Own goals
    pts += int(stats.get("own_goals") or 0) * -2

    return pts


def build_breakdown(player_id: str, stats: dict, is_captain: bool) -> dict:
    """Full readable breakdown for Stats view."""
    p = get_player(player_id)
    if not p:
        return {}

    pos     = p["position"]
    minutes = int(stats.get("minutes_played") or 0)
    goals   = int(stats.get("goals") or 0)
    assists = int(stats.get("assists") or 0)
    yellow  = int(stats.get("yellow_cards") or 0)
    red     = int(stats.get("red_cards") or 0)
    yr      = int(stats.get("yellow_then_red") or 0)
    saves   = int(stats.get("saves") or 0)
    pen_sv  = int(stats.get("penalty_saved") or 0)
    pen_ms  = int(stats.get("penalty_miss") or 0)
    pen_ea  = int(stats.get("penalty_earned") or 0)
    pen_co  = int(stats.get("penalty_conceded") or 0)
    conceded= int(stats.get("goals_conceded") or 0)
    own_g   = int(stats.get("own_goals") or 0)
    clean   = bool(stats.get("clean_sheet"))
    tackles       = int(stats.get("tackles") or 0)
    interceptions = int(stats.get("interceptions") or 0)
    blks          = int(stats.get("blocks") or 0)
    def_acts      = tackles + interceptions + blks

    goal_pts = {"GK": 6, "DEF": 6, "MF": 5, "FW": 4}.get(pos, 4)
    cs_pts   = {"GK": 4, "DEF": 4, "MF": 1, "FW": 0}.get(pos, 0)

    raw  = calc_points(player_id, stats)
    final= raw * 2 if is_captain else raw

    return {
        "minutes_played":   minutes,
        "goals":            goals,
        "assists":          assists,
        "yellow_cards":     yellow,
        "red_cards":        red,
        "yellow_then_red":  yr,
        "saves":            saves,
        "penalty_saved":    pen_sv,
        "penalty_miss":     pen_ms,
        "penalty_earned":   pen_ea,
        "penalty_conceded": pen_co,
        "goals_conceded":   conceded,
        "own_goals":        own_g,
        "clean_sheet":      clean,
        "def_actions":      def_acts,
        "pts_appearance":   (1 if minutes > 0 else 0) + (1 if minutes >= 60 else 0),
        "pts_goals":        goals * goal_pts,
        "pts_assists":      assists * 3,
        "pts_clean_sheet":  cs_pts if (clean and minutes >= 60) else 0,
        "pts_conceded":     -(conceded // 2) if pos in ("GK", "DEF") else 0,
        "pts_saves":        (saves // 3) if pos == "GK" else 0,
        "pts_pen_saved":    pen_sv * 5,
        "pts_pen_miss":     pen_ms * -2,
        "pts_pen_earned":   pen_ea * 2,
        "pts_pen_conceded": pen_co * -1,
        "pts_yellow":       yellow * -1,
        "pts_red":          red * -3,
        "pts_yr":           yr * -1,
        "pts_own_goals":    own_g * -2,
        "pts_def_actions":  def_acts // 3,
        "captain":          is_captain,
        "captain_mult":     2 if is_captain else 1,
        "base_pts":         raw,
        "total":            final,
    }
