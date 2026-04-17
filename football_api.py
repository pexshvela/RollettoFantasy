"""
football_api.py — SportAPI7 (SofaScore-based) via RapidAPI
Base URL: https://sportapi7.p.rapidapi.com

Endpoints used:
  GET /api/v1/sport/football/scheduled-events/{date}
      → all football matches on a date; filter by tournament.uniqueTournament.id == 7 (UCL)

  GET /api/v1/event/{id}
      → match details: score, status, teams

  GET /api/v1/event/{id}/incidents
      → goals (scorer + assist), yellow/red cards, substitutions

  GET /api/v1/event/{id}/lineups
      → confirmed lineups: starters + bench + minutes played per player

  GET /api/v1/event/{id}/statistics  (optional, team-level)
      → possession, shots etc. (not needed for player points but useful for display)
"""
import logging
import asyncio
import aiohttp
import config

logger = logging.getLogger(__name__)

BASE    = "https://sportapi7.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key":  config.API_FOOTBALL_KEY,
    "X-RapidAPI-Host": "sportapi7.p.rapidapi.com",
}

# SofaScore IDs (uniqueTournament.id)
UCL_TOURNAMENT_ID = 7   # UEFA Champions League
# Other common ones for /settournaments:
# Premier League = 17, La Liga = 8, Bundesliga = 35, Serie A = 23
# Europa League = 679, Conference League = 17015
# World Cup = 16


async def _get(path: str, params: dict = None) -> tuple[int, dict | None]:
    url = f"{BASE}/{path.lstrip('/')}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=HEADERS, params=params,
                             timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return 200, await resp.json()
                logger.error("HTTP %s for %s", resp.status, url)
                return resp.status, None
    except Exception as e:
        logger.error("API error (%s): %s", path, e)
        return 0, None


# ── 1. List matches by date ───────────────────────────────────────────────────

async def get_matches_by_date(date_str: str, tournament_ids: list[int] = None) -> list[dict]:
    """
    Get all football matches on date_str, optionally filtered by tournament IDs.
    date_str: 'YYYY-MM-DD'
    tournament_ids: list of SofaScore uniqueTournament.id values (default: [7] = UCL)
    Returns list of normalized match dicts.
    """
    if tournament_ids is None:
        tournament_ids = [UCL_TOURNAMENT_ID]

    code, data = await _get(f"/api/v1/sport/football/scheduled-events/{date_str}")
    if code != 200 or not data:
        logger.error("scheduled-events HTTP %s for %s", code, date_str)
        return []

    events = data.get("events") or []
    matches = []

    for e in events:
        tid = (e.get("tournament") or {}).get("uniqueTournament", {}).get("id")
        if tid not in tournament_ids:
            continue

        matches.append(_parse_event(e))

    logger.info("Found %d matching matches on %s", len(matches), date_str)
    return matches


def _parse_event(e: dict) -> dict:
    """Normalize a SofaScore event dict into our standard match format."""
    import datetime

    home = e.get("homeTeam") or {}
    away = e.get("awayTeam") or {}

    hs = e.get("homeScore") or {}
    as_ = e.get("awayScore") or {}
    home_score = int(hs.get("current") or hs.get("normaltime") or 0)
    away_score = int(as_.get("current") or as_.get("normaltime") or 0)

    status_obj = e.get("status") or {}
    status_type = str(status_obj.get("type") or "").lower()
    status_desc = str(status_obj.get("description") or "").lower()
    if status_type in ("finished",) or "finished" in status_desc or "ft" in status_desc:
        status = "final"
    elif status_type in ("inprogress",) or "progress" in status_type or "live" in status_desc:
        status = "in_progress"
    else:
        status = "scheduled"

    ts = e.get("startTimestamp")
    date_str = datetime.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d") if ts else ""

    tournament = e.get("tournament") or {}
    t_name = tournament.get("name") or tournament.get("uniqueTournament", {}).get("name") or ""
    t_id   = tournament.get("uniqueTournament", {}).get("id", 0)

    return {
        "id":             str(e.get("id", "")),
        "home_team":      home.get("name") or home.get("shortName") or "?",
        "away_team":      away.get("name") or away.get("shortName") or "?",
        "home_score":     home_score,
        "away_score":     away_score,
        "home_team_id":   str(home.get("id", "")),
        "away_team_id":   str(away.get("id", "")),
        "status":         status,
        "date":           date_str,
        "tournament":     t_name,
        "tournament_id":  t_id,
        "tournament_url": f"/football/ucl/{t_id}/",  # synthetic URL for filter compat
    }


# ── 2. Match details ──────────────────────────────────────────────────────────

async def get_match_details(event_id: str) -> dict | None:
    code, data = await _get(f"/api/v1/event/{event_id}")
    if code != 200 or not data:
        return None
    e = data.get("event") or data
    return _parse_event(e)


# ── 3. Incidents (goals, cards, assists) ─────────────────────────────────────

async def get_match_incidents(event_id: str) -> list[dict]:
    """
    Returns list of goal/card events.
    SofaScore incidents include: goal, yellowCard, redCard, yellowRedCard,
    substitution, missedPenalty, etc.
    """
    code, data = await _get(f"/api/v1/event/{event_id}/incidents")
    if code != 200 or not data:
        return []

    incidents_raw = data.get("incidents") or []
    events = []

    for inc in incidents_raw:
        itype = str(inc.get("incidentType") or inc.get("type") or "").lower()
        iclass = str(inc.get("incidentClass") or inc.get("class") or "").lower()

        if itype == "goal":
            if "own" in iclass:
                etype = "own_goal"
            elif "penalty" in iclass:
                etype = "goal"  # penalty goal still counts as goal
            else:
                etype = "goal"
        elif itype == "card":
            if "red" in iclass and "yellow" not in iclass:
                etype = "red_card"
            elif "yellowred" in iclass or "yellow_red" in iclass:
                etype = "yellow_then_red"
            else:
                etype = "yellow_card"
        elif itype == "missedpenalty" or (itype == "penalty" and "miss" in iclass):
            etype = "penalty_miss"
        else:
            continue

        # Player name
        player_obj = inc.get("player") or {}
        player_name = player_obj.get("name") or player_obj.get("shortName") or ""

        # Assist
        assist_obj = inc.get("assist1") or inc.get("assist") or {}
        assist_name = assist_obj.get("name") or assist_obj.get("shortName") or ""

        minute = str(inc.get("time") or inc.get("minute") or "")
        # isHome: True = home team, False = away team
        is_home = inc.get("isHome")
        team = "home" if is_home else "away"

        events.append({
            "type":   etype,
            "minute": minute,
            "player": player_name,
            "assist": assist_name,
            "team":   team,
        })

    return events


# ── 4. Lineups ────────────────────────────────────────────────────────────────

async def get_lineups(event_id: str) -> dict:
    """
    Returns:
    {
      home_starters: [{name, player_id, position, minutes_played, team_id}],
      away_starters: [...],
      home_subs:     [{name, player_id, substitute_in_time}],
      away_subs:     [...],
      home_team_id:  str,
      away_team_id:  str,
      played_ids:    set of player_ids who played (starters + used subs),
      starter_ids:   set of player_ids who started,
    }
    """
    code, data = await _get(f"/api/v1/event/{event_id}/lineups")
    if code != 200 or not data:
        logger.warning("get_lineups HTTP %s for %s", code, event_id)
        return {}

    result = {
        "home_starters": [], "away_starters": [],
        "home_subs":     [], "away_subs":     [],
        "home_team_id":  "", "away_team_id":  "",
        "played_ids":    set(),
        "starter_ids":   set(),
    }

    for side in ("home", "away"):
        side_data = data.get(side) or {}
        team_obj  = side_data.get("team") or {}
        team_id   = str(team_obj.get("id") or "")
        result[f"{side}_team_id"] = team_id

        players = side_data.get("players") or []
        for p in players:
            player_obj = p.get("player") or {}
            pid        = str(player_obj.get("id") or "")
            name       = player_obj.get("name") or player_obj.get("shortName") or ""
            position   = p.get("position") or p.get("positionName") or ""
            stats      = p.get("statistics") or {}
            minutes    = int(stats.get("minutesPlayed") or stats.get("minutes") or 0)
            starter    = p.get("substitute") is False or p.get("type") == "starter"

            entry = {
                "name":           name,
                "player_id":      pid,
                "sofascore_name": player_obj.get("shortName") or name,
                "position":       position,
                "minutes_played": minutes,
                "team_id":        team_id,
                "side":           side,
                "stats":          stats,  # full per-player stats from lineups
            }

            if starter:
                result[f"{side}_starters"].append(entry)
                if pid:
                    result["starter_ids"].add(pid)
                    if minutes > 0:
                        result["played_ids"].add(pid)
            else:
                sub_in = stats.get("substituteInExpandedMinute") or stats.get("substituteIn") or 0
                entry["substitute_in"] = sub_in
                result[f"{side}_subs"].append(entry)
                if pid and minutes > 0:
                    result["played_ids"].add(pid)

    logger.info("Lineups: %d home, %d away starters",
                len(result["home_starters"]), len(result["away_starters"]))
    return result


# ── 5. Player stats from lineups ──────────────────────────────────────────────

def extract_player_stats_from_lineups(lineups: dict) -> dict:
    """
    SofaScore lineups already contain per-player stats inside p["statistics"].
    Extract and normalize into our stats format.
    Returns {sofascore_player_id: stats_dict}
    """
    result = {}
    all_sides = [
        ("home", lineups.get("home_starters", []) + lineups.get("home_subs", [])),
        ("away", lineups.get("away_starters", []) + lineups.get("away_subs", [])),
    ]

    for side, players in all_sides:
        for p in players:
            pid  = p.get("player_id", "")
            name = p.get("name", "")
            raw  = p.get("stats") or {}

            def sv(key: str) -> int:
                v = raw.get(key) or 0
                try:
                    return int(float(v))
                except Exception:
                    return 0

            # Goals: goals - own goals
            goals    = sv("goals") or sv("expectedGoals") and 0 or 0
            # SofaScore uses "goals" directly
            goals    = sv("goals")
            own_goals= sv("ownGoals")
            net_goals= max(0, goals - own_goals)

            minutes  = sv("minutesPlayed") or sv("minutes") or p.get("minutes_played", 0)

            result[pid] = {
                "name":             name,
                "sofascore_name":   p.get("sofascore_name", name),
                "player_id":        pid,
                "team_id":          p.get("team_id", ""),
                "side":             side,
                "position":         p.get("position", ""),
                "minutes_played":   minutes,
                "goals":            net_goals,
                "own_goals":        own_goals,
                "assists":          sv("goalAssist") or sv("assists"),
                "yellow_cards":     sv("yellowCards") or sv("yellowCard"),
                "red_cards":        sv("redCards") or sv("redCard"),
                "yellow_then_red":  sv("yellowRedCards") or sv("yellowRedCard"),
                "penalty_miss":     sv("missedPenalties") or sv("penaltyMiss"),
                "penalty_earned":   sv("penaltiesWon") or sv("penaltyEarned"),
                "penalty_conceded": sv("penaltiesConceded") or 0,
                "penalty_saved":    sv("savedPenalties") or sv("penaltySaved"),
                "saves":            sv("saves") or sv("totalSaves"),
                "tackles":          sv("tackleWon") or sv("tackles"),
                "interceptions":    sv("interceptions") or sv("interceptionWon"),
                "blocks":           sv("blockedScoringAttempt") or sv("blocks"),
                "goals_conceded":   0,    # set by scheduler
                "clean_sheet":      False, # set by scheduler
                "in_lineup":        minutes > 0,
            }
            if name:
                result[name.lower()] = result[pid]

    return result


# ── 6. Full match fetch ────────────────────────────────────────────────────────

async def fetch_full_match(event_id: str) -> dict | None:
    """
    Fetch all data for a match: details + lineups + player stats + incidents.
    """
    details = await get_match_details(event_id)
    if not details:
        return None

    lineups  = await get_lineups(event_id)
    events   = await get_match_incidents(event_id)

    # Player stats come from lineups (SofaScore embeds them)
    player_stats = extract_player_stats_from_lineups(lineups)

    details["lineups"]       = lineups
    details["player_stats"]  = player_stats
    details["events"]        = events
    details["played_ids"]    = lineups.get("played_ids", set())
    details["starter_ids"]   = lineups.get("starter_ids", set())

    return details


# ── 7. Auto-scan today + yesterday ───────────────────────────────────────────

async def get_ucl_matches_today_and_yesterday(tournament_ids: list[int] = None) -> list[dict]:
    from datetime import date, timedelta
    if tournament_ids is None:
        tournament_ids = [UCL_TOURNAMENT_ID]
    matches = []
    for d in [date.today(), date.today() - timedelta(days=1)]:
        found = await get_matches_by_date(d.isoformat(), tournament_ids)
        matches.extend(found)
    return matches


async def get_active_keywords():
    """For compatibility with tournament filter — returns list of tournament IDs as ints."""
    try:
        import sheets as _sheets
        kws = await _sheets.get_tournament_keywords()
        return kws
    except Exception:
        return ["champions-league"]

async def get_upcoming_matches(tournament_ids: list[int] = None, days_ahead: int = 14) -> list[dict]:
    """Scan next N days for matches in the given tournaments."""
    from datetime import date, timedelta
    if tournament_ids is None:
        tournament_ids = [UCL_TOURNAMENT_ID]
    matches = []
    for i in range(1, days_ahead + 1):
        d = (date.today() + timedelta(days=i)).isoformat()
        found = await get_matches_by_date(d, tournament_ids)
        matches.extend(found)
        if matches:
            break  # stop at the first day that has matches
    return matches
