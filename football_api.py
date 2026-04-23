"""
football_api.py — api-football v3 (api-football-v1.p.rapidapi.com)

Key: e23260ce6329642ba416e6e185140894
Host: api-football-v1.p.rapidapi.com
Base: https://api-football-v1.p.rapidapi.com/v3

League IDs:
  UCL = 2   (season 2024)
  PL  = 39  (season 2024)
  La Liga = 140, Bundesliga = 78, Serie A = 135, Ligue 1 = 61
  Europa League = 3, Conference League = 848
  World Cup = 1

Endpoints used:
  GET /fixtures?league=2&season=2024         → all UCL fixtures
  GET /fixtures?id=123456                    → single match details
  GET /fixtures/lineups?fixture=123456       → lineups
  GET /fixtures/players?fixture=123456       → per-player stats
  GET /fixtures/events?fixture=123456        → goals, cards, assists
"""
import logging
import asyncio
import aiohttp
import config

logger = logging.getLogger(__name__)

BASE    = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": config.API_FOOTBALL_KEY,
}

# api-football league IDs
LEAGUE_IDS = {
    "ucl":        2,
    "pl":         39,
    "laliga":     140,
    "bundesliga": 78,
    "seriea":     135,
    "ligue1":     61,
    "el":         3,
    "ecl":        848,
    "wc":         1,
}

# Current season per league
SEASONS = {
    2:   2024,
    39:  2024,
    140: 2024,
    78:  2024,
    135: 2024,
    61:  2024,
    3:   2024,
    848: 2024,
}

# Map from our internal tournament IDs (used in bot_settings) to api-football IDs
# When admin does /settournaments ucl, we store 2 (api-football ID)
SOFASCORE_TO_AF = {
    7:   2,    # UCL
    17:  39,   # PL
    8:   140,  # La Liga
    35:  78,   # Bundesliga
    23:  135,  # Serie A
    34:  61,   # Ligue 1
    679: 3,    # Europa League
}


async def _get(endpoint: str, params: dict = None) -> tuple[int, dict | None]:
    url = f"{BASE}/{endpoint.lstrip('/')}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=HEADERS, params=params,
                             timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    return 200, await resp.json()
                logger.error("HTTP %s for %s params=%s", resp.status, url, params)
                return resp.status, None
    except Exception as e:
        logger.error("API error (%s): %s", endpoint, e)
        return 0, None


# ── 1. Get all fixtures for a league ─────────────────────────────────────────

async def get_fixtures(af_league_id: int) -> list[dict]:
    """Get ALL fixtures for a league/season."""
    season = SEASONS.get(af_league_id, 2024)
    code, data = await _get("/fixtures", {"league": af_league_id, "season": season})
    if code != 200 or not data:
        logger.error("get_fixtures HTTP %s for league %s", code, af_league_id)
        return []
    return [_parse_fixture(f) for f in (data.get("response") or [])]


def _parse_fixture(f: dict) -> dict:
    import datetime
    fixture  = f.get("fixture") or {}
    teams    = f.get("teams") or {}
    goals    = f.get("goals") or {}
    league   = f.get("league") or {}
    home     = teams.get("home") or {}
    away     = teams.get("away") or {}
    status   = fixture.get("status") or {}

    status_short = str(status.get("short") or "").upper()
    if status_short in ("FT", "AET", "PEN"):
        match_status = "final"
    elif status_short in ("1H", "HT", "2H", "ET", "P", "LIVE", "BT"):
        match_status = "in_progress"
    else:
        match_status = "scheduled"

    kickoff_ts = fixture.get("timestamp") or 0
    if kickoff_ts:
        dt       = datetime.datetime.fromtimestamp(int(kickoff_ts))
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
    else:
        raw_date = str(fixture.get("date") or "")
        date_str = raw_date[:10]
        time_str = raw_date[11:16]

    return {
        "id":                str(fixture.get("id", "")),
        "home_team":         home.get("name", "?"),
        "away_team":         away.get("name", "?"),
        "home_score":        int(goals.get("home") or 0),
        "away_score":        int(goals.get("away") or 0),
        "home_team_id":      str(home.get("id", "")),
        "away_team_id":      str(away.get("id", "")),
        "status":            match_status,
        "date":              date_str,
        "time":              time_str,
        "kickoff_timestamp": int(kickoff_ts),
        "tournament":        league.get("name", ""),
        "tournament_url":    f"/football/league/{league.get('id', '')}/",
        "league_id":         league.get("id", 0),
    }


# ── 2. Single match details ───────────────────────────────────────────────────

async def get_match_details(fixture_id: str) -> dict | None:
    code, data = await _get("/fixtures", {"id": fixture_id})
    if code != 200 or not data:
        return None
    resp = data.get("response") or []
    return _parse_fixture(resp[0]) if resp else None


# ── 3. Lineups ────────────────────────────────────────────────────────────────

async def get_lineups(fixture_id: str) -> dict:
    code, data = await _get("/fixtures/lineups", {"fixture": fixture_id})
    if code != 200 or not data:
        return {}

    result = {
        "home_starters": [], "away_starters": [],
        "home_subs":     [], "away_subs":     [],
        "home_team_id":  "", "away_team_id":  "",
        "played_ids":    set(),
        "starter_ids":   set(),
    }

    sides = data.get("response") or []
    for i, side_data in enumerate(sides):
        side    = "home" if i == 0 else "away"
        team    = side_data.get("team") or {}
        team_id = str(team.get("id", ""))
        result[f"{side}_team_id"] = team_id

        for p_entry in (side_data.get("startXI") or []):
            p   = p_entry.get("player") or {}
            pid = str(p.get("id", ""))
            entry = {
                "name": p.get("name", ""), "player_id": pid,
                "team_id": team_id, "side": side,
                "position": p.get("pos", ""), "number": str(p.get("number", "")),
            }
            result[f"{side}_starters"].append(entry)
            if pid:
                result["starter_ids"].add(pid)
                result["played_ids"].add(pid)

        for p_entry in (side_data.get("substitutes") or []):
            p   = p_entry.get("player") or {}
            pid = str(p.get("id", ""))
            result[f"{side}_subs"].append({
                "name": p.get("name", ""), "player_id": pid,
                "team_id": team_id, "side": side,
            })

    return result


# ── 4. Player stats ───────────────────────────────────────────────────────────

async def get_player_stats(fixture_id: str) -> dict | None:
    code, data = await _get("/fixtures/players", {"fixture": fixture_id})
    if code != 200 or not data:
        return None

    result = {}
    for team_data in (data.get("response") or []):
        team_id = str((team_data.get("team") or {}).get("id", ""))
        for p_entry in (team_data.get("players") or []):
            p     = p_entry.get("player") or {}
            stats = (p_entry.get("statistics") or [{}])[0]
            pid   = str(p.get("id", ""))
            name  = p.get("name", "")

            games    = stats.get("games")    or {}
            goals_s  = stats.get("goals")    or {}
            cards_s  = stats.get("cards")    or {}
            tackles_s= stats.get("tackles")  or {}
            penalty_s= stats.get("penalty")  or {}

            minutes = int(games.get("minutes") or 0)

            s = {
                "name":             name,
                "player_id":        pid,
                "team_id":          team_id,
                "position":         games.get("position", ""),
                "minutes_played":   minutes,
                "in_lineup":        minutes > 0,
                "goals":            int(goals_s.get("total") or 0),
                "own_goals":        int(goals_s.get("owngoals") or 0),
                "assists":          int(goals_s.get("assists") or 0),
                "yellow_cards":     int(cards_s.get("yellow") or 0),
                "red_cards":        int(cards_s.get("red") or 0),
                "yellow_then_red":  int(cards_s.get("yellowred") or 0),
                "saves":            int(goals_s.get("saves") or 0),
                "penalty_saved":    int(penalty_s.get("saved") or 0),
                "penalty_miss":     int(penalty_s.get("missed") or 0),
                "penalty_earned":   int(penalty_s.get("won") or 0),
                "penalty_conceded": int(penalty_s.get("commited") or 0),
                "tackles":          int(tackles_s.get("total") or 0),
                "interceptions":    int(tackles_s.get("interceptions") or 0),
                "blocks":           int(tackles_s.get("blocks") or 0),
                "goals_conceded":   0,
                "clean_sheet":      False,
            }
            if pid:   result[pid]          = s
            if name:  result[name.lower()] = s

    return result


# ── 5. Match events ───────────────────────────────────────────────────────────

async def get_match_incidents(fixture_id: str) -> list[dict]:
    code, data = await _get("/fixtures/events", {"fixture": fixture_id})
    if code != 200 or not data:
        return []

    events = []
    for e in (data.get("response") or []):
        etype_raw  = str(e.get("type") or "").lower()
        detail_raw = str(e.get("detail") or "").lower()
        player_obj = e.get("player") or {}
        assist_obj = e.get("assist") or {}
        minute     = str((e.get("time") or {}).get("elapsed") or "")
        team_name  = (e.get("team") or {}).get("name", "")

        if etype_raw == "goal":
            etype = "own_goal" if "own" in detail_raw else "goal"
        elif etype_raw == "card":
            if "yellow" in detail_raw and "red" in detail_raw:
                etype = "yellow_then_red"
            elif "red" in detail_raw:
                etype = "red_card"
            else:
                etype = "yellow_card"
        else:
            continue

        events.append({
            "type":   etype,
            "minute": minute,
            "player": player_obj.get("name", ""),
            "assist": assist_obj.get("name", ""),
            "team":   team_name,
        })
    return events


# ── 6. Full match fetch ────────────────────────────────────────────────────────

async def fetch_full_match(fixture_id: str) -> dict | None:
    details = await get_match_details(fixture_id)
    if not details:
        return None
    lineups      = await get_lineups(fixture_id)
    player_stats = await get_player_stats(fixture_id)
    events       = await get_match_incidents(fixture_id)
    details["lineups"]      = lineups
    details["player_stats"] = player_stats or {}
    details["events"]       = events
    details["played_ids"]   = lineups.get("played_ids", set())
    details["starter_ids"]  = lineups.get("starter_ids", set())
    return details


# ── 7. All fixtures for active tournaments ────────────────────────────────────

async def get_all_tournament_fixtures(tournament_ids: list[int] = None) -> list[dict]:
    """
    Fetch all fixtures for given tournament IDs.
    tournament_ids: api-football league IDs (2 for UCL, 39 for PL etc.)
    """
    if not tournament_ids:
        tournament_ids = [2]  # UCL default

    # Convert from SofaScore IDs if needed
    af_ids = []
    for tid in tournament_ids:
        af_id = SOFASCORE_TO_AF.get(tid, tid)  # pass through if already api-football ID
        af_ids.append(af_id)

    all_matches = []
    seen = set()
    for af_id in af_ids:
        matches = await get_fixtures(af_id)
        for m in matches:
            if m["id"] not in seen:
                seen.add(m["id"])
                all_matches.append(m)
        await asyncio.sleep(0.5)

    return sorted(all_matches, key=lambda x: (x["date"], x.get("time", "")))


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
