"""
football_api.py — Sofascore API (sofascore.p.rapidapi.com)

Host: sofascore.p.rapidapi.com
Key endpoints:
  GET /tournaments/get-seasons?tournamentId=17        → season IDs
  GET /tournaments/get-next-matches?tournamentId=17&seasonId=X&pageIndex=0  → upcoming
  GET /tournaments/get-last-matches?tournamentId=17&seasonId=X&pageIndex=0  → past
  GET /matches/detail?matchId=X                       → score, status, teams
  GET /matches/get-lineups?matchId=X                  → who played + stats
  GET /matches/get-incidents?matchId=X                → goals, cards, assists

Tournament IDs (Sofascore):
  UCL = 17, PL = 17... wait — UCL is actually 7 in SofaScore native.
  The example uses tournamentId=17 which maps to UCL in THIS api wrapper.
  Confirm with /tournaments/list?categoryId=1
"""
import logging
import asyncio
import aiohttp
import config

logger = logging.getLogger(__name__)

BASE    = "https://sofascore.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-host": "sofascore.p.rapidapi.com",
    "x-rapidapi-key":  config.API_FOOTBALL_KEY,
    "Content-Type":    "application/json",
}

# Known tournament IDs for this API — confirm with /testtournaments
TOURNAMENT_IDS = {
    "ucl":        17,
    "pl":         17,   # update after /testtournaments
    "laliga":     8,
    "bundesliga": 35,
    "seriea":     23,
    "ligue1":     34,
    "el":         679,
}

# Cache season IDs to avoid repeated calls
_season_cache: dict[int, int] = {}


async def _get(endpoint: str, params: dict = None) -> tuple[int, dict | None]:
    url = f"{BASE}/{endpoint.lstrip('/')}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=HEADERS, params=params,
                             timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return 200, await resp.json()
                logger.error("HTTP %s for %s params=%s", resp.status, url, params)
                return resp.status, None
    except Exception as e:
        logger.error("API error (%s): %s", endpoint, e)
        return 0, None


# ── Seasons ───────────────────────────────────────────────────────────────────

async def get_current_season_id(tournament_id: int) -> int | None:
    """Get the most recent season ID for a tournament."""
    if tournament_id in _season_cache:
        return _season_cache[tournament_id]

    code, data = await _get("/tournaments/get-seasons",
                            {"tournamentId": tournament_id})
    if code != 200 or not data:
        return None

    seasons = data.get("seasons") or []
    if not seasons:
        return None

    # Most recent = first in list
    season_id = seasons[0].get("id") or seasons[0].get("seasonId")
    if season_id:
        _season_cache[tournament_id] = int(season_id)
        logger.info("Tournament %d → season %d", tournament_id, season_id)
    return int(season_id) if season_id else None


# ── Fixtures ──────────────────────────────────────────────────────────────────

async def get_fixtures(tournament_id: int) -> list[dict]:
    """
    Get ALL fixtures (past + upcoming) for a tournament.
    Paginates through both get-last-matches and get-next-matches.
    """
    season_id = await get_current_season_id(tournament_id)
    if not season_id:
        logger.error("Could not get season ID for tournament %d", tournament_id)
        return []

    all_matches = []

    # Upcoming matches — paginate until empty
    for page in range(10):  # max 10 pages
        code, data = await _get("/tournaments/get-next-matches", {
            "tournamentId": tournament_id,
            "seasonId":     season_id,
            "pageIndex":    page,
        })
        if code != 200 or not data:
            break
        events = data.get("events") or []
        if not events:
            break
        for e in events:
            all_matches.append(_parse_event(e))
        if len(events) < 10:  # less than full page = last page
            break
        await asyncio.sleep(0.3)

    # Past matches — paginate
    for page in range(20):  # more pages for past
        code, data = await _get("/tournaments/get-last-matches", {
            "tournamentId": tournament_id,
            "seasonId":     season_id,
            "pageIndex":    page,
        })
        if code != 200 or not data:
            break
        events = data.get("events") or []
        if not events:
            break
        for e in events:
            all_matches.append(_parse_event(e))
        if len(events) < 10:
            break
        await asyncio.sleep(0.3)

    # Deduplicate
    seen = set()
    unique = []
    for m in all_matches:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique.append(m)

    return sorted(unique, key=lambda x: (x["date"], x.get("time", "")))


def _parse_event(e: dict) -> dict:
    """Normalize a Sofascore event to our standard format."""
    import datetime

    home = e.get("homeTeam") or {}
    away = e.get("awayTeam") or {}

    hs  = e.get("homeScore") or {}
    as_ = e.get("awayScore") or {}
    home_score = int(hs.get("current") or hs.get("normaltime") or 0)
    away_score = int(as_.get("current") or as_.get("normaltime") or 0)

    status_obj  = e.get("status") or {}
    status_type = str(status_obj.get("type") or "").lower()
    status_desc = str(status_obj.get("description") or "").lower()

    if status_type == "finished" or "finished" in status_desc:
        status = "final"
    elif status_type == "inprogress" or "progress" in status_type:
        status = "in_progress"
    else:
        status = "scheduled"

    ts = e.get("startTimestamp") or e.get("timestamp")
    if ts:
        dt       = datetime.datetime.fromtimestamp(int(ts))
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
    else:
        date_str = ""
        time_str = ""

    tournament = e.get("tournament") or {}
    ut         = tournament.get("uniqueTournament") or {}

    return {
        "id":                str(e.get("id", "") or e.get("matchId", "")),
        "home_team":         home.get("name") or home.get("shortName") or "?",
        "away_team":         away.get("name") or away.get("shortName") or "?",
        "home_score":        home_score,
        "away_score":        away_score,
        "home_team_id":      str(home.get("id", "")),
        "away_team_id":      str(away.get("id", "")),
        "status":            status,
        "date":              date_str,
        "time":              time_str,
        "kickoff_timestamp": int(ts) if ts else 0,
        "tournament":        ut.get("name") or tournament.get("name") or "",
        "tournament_url":    f"/tournament/{ut.get('id', '')}",
    }


# ── Single match details ──────────────────────────────────────────────────────

async def get_match_details(match_id: str) -> dict | None:
    code, data = await _get("/matches/detail", {"matchId": match_id})
    if code != 200 or not data:
        return None
    e = data.get("event") or data.get("match") or data
    return _parse_event(e)


# ── Lineups ───────────────────────────────────────────────────────────────────

async def get_lineups(match_id: str) -> dict:
    code, data = await _get("/matches/get-lineups", {"matchId": match_id})
    if code != 200 or not data:
        logger.warning("get_lineups HTTP %s for %s", code, match_id)
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
            stats_raw  = p.get("statistics") or {}
            minutes    = int(stats_raw.get("minutesPlayed") or stats_raw.get("minutes") or 0)
            is_sub     = bool(p.get("substitute"))

            entry = {
                "name":           name,
                "player_id":      pid,
                "sofascore_name": player_obj.get("shortName") or name,
                "position":       p.get("position") or p.get("positionName") or "",
                "minutes_played": minutes,
                "team_id":        team_id,
                "side":           side,
                "stats":          stats_raw,
            }

            if not is_sub:
                result[f"{side}_starters"].append(entry)
                if pid:
                    result["starter_ids"].add(pid)
                    if minutes > 0:
                        result["played_ids"].add(pid)
            else:
                result[f"{side}_subs"].append(entry)
                if pid and minutes > 0:
                    result["played_ids"].add(pid)

    return result


def extract_player_stats_from_lineups(lineups: dict) -> dict:
    """Extract per-player stats from lineups response."""
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

            def sv(key):
                v = raw.get(key) or 0
                try: return int(float(v))
                except: return 0

            goals     = sv("goals")
            own_goals = sv("ownGoals")
            minutes   = sv("minutesPlayed") or sv("minutes") or p.get("minutes_played", 0)

            stats = {
                "name":             name,
                "sofascore_name":   p.get("sofascore_name", name),
                "player_id":        pid,
                "team_id":          p.get("team_id", ""),
                "side":             side,
                "position":         p.get("position", ""),
                "minutes_played":   minutes,
                "in_lineup":        minutes > 0,
                "goals":            max(0, goals - own_goals),
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
                "goals_conceded":   0,
                "clean_sheet":      False,
            }
            if pid:
                result[pid] = stats
            if name:
                result[name.lower()] = stats
    return result


# ── Incidents ─────────────────────────────────────────────────────────────────

async def get_match_incidents(match_id: str) -> list[dict]:
    code, data = await _get("/matches/get-incidents", {"matchId": match_id})
    if code != 200 or not data:
        return []

    incidents_raw = data.get("incidents") or []
    events = []

    for inc in incidents_raw:
        itype  = str(inc.get("incidentType") or inc.get("type") or "").lower()
        iclass = str(inc.get("incidentClass") or inc.get("class") or "").lower()

        if itype == "goal":
            etype = "own_goal" if "own" in iclass else "goal"
        elif itype == "card":
            if "yellowred" in iclass:
                etype = "yellow_then_red"
            elif "red" in iclass:
                etype = "red_card"
            else:
                etype = "yellow_card"
        elif itype == "missedpenalty" or ("penalty" in itype and "miss" in iclass):
            etype = "penalty_miss"
        else:
            continue

        player_obj = inc.get("player") or {}
        assist_obj = inc.get("assist1") or inc.get("assist") or {}

        events.append({
            "type":   etype,
            "minute": str(inc.get("time") or inc.get("minute") or ""),
            "player": player_obj.get("name") or player_obj.get("shortName") or "",
            "assist": assist_obj.get("name") or assist_obj.get("shortName") or "",
            "team":   "home" if inc.get("isHome") else "away",
        })

    return events


# ── Full match fetch ──────────────────────────────────────────────────────────

async def fetch_full_match(match_id: str) -> dict | None:
    details = await get_match_details(match_id)
    if not details:
        return None

    lineups      = await get_lineups(match_id)
    player_stats = extract_player_stats_from_lineups(lineups)
    events       = await get_match_incidents(match_id)

    details["lineups"]      = lineups
    details["player_stats"] = player_stats
    details["events"]       = events
    details["played_ids"]   = lineups.get("played_ids", set())
    details["starter_ids"]  = lineups.get("starter_ids", set())

    return details


# ── All fixtures for active tournaments ───────────────────────────────────────

async def get_all_tournament_fixtures(tournament_ids: list[int] = None) -> list[dict]:
    if not tournament_ids:
        tournament_ids = [7]

    all_matches = []
    for tid in tournament_ids:
        matches = await get_fixtures(tid)
        all_matches.extend(matches)
        await asyncio.sleep(0.5)

    seen = set()
    unique = []
    for m in all_matches:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique.append(m)

    return sorted(unique, key=lambda x: (x["date"], x.get("time", "")))


async def get_ucl_matches_today_and_yesterday(tournament_ids: list[int] = None) -> list[dict]:
    from datetime import date, timedelta
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    all_m     = await get_all_tournament_fixtures(tournament_ids)
    return [m for m in all_m
            if m["date"] in (today, yesterday) and m["status"] == "final"]


async def get_active_keywords():
    try:
        import sheets as _s
        return await _s.get_tournament_keywords()
    except Exception:
        return ["champions-league"]
