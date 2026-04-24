"""
football_api.py — api-football direct (v3.football.api-sports.io)
Key header: x-apisports-key

Endpoints:
  GET /fixtures?league=X&season=Y    → all fixtures
  GET /fixtures?id=X                 → single match
  GET /fixtures/lineups?fixture=X    → lineups
  GET /fixtures/players?fixture=X    → player stats
  GET /fixtures/events?fixture=X     → goals/cards
"""
import logging
import asyncio
import aiohttp
from datetime import datetime, timezone
import config

logger = logging.getLogger(__name__)

BASE    = config.API_FOOTBALL_BASE
HEADERS = {"x-apisports-key": config.API_FOOTBALL_KEY}

LEAGUE_IDS = config.LEAGUE_IDS


async def _get(endpoint: str, params: dict = None) -> tuple[int, dict | None]:
    url = f"{BASE}/{endpoint.lstrip('/')}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=HEADERS, params=params,
                             timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    return 200, await resp.json()
                body = await resp.text()
                logger.error("HTTP %s %s | %s", resp.status, url, body[:200])
                return resp.status, None
    except Exception as e:
        logger.error("API error (%s): %s", endpoint, e)
        return 0, None


# ── 1. Get all fixtures ───────────────────────────────────────────────────────

async def get_all_fixtures(tournament: str) -> list[dict]:
    """Fetch all fixtures for a tournament (ucl or pl)."""
    cfg  = LEAGUE_IDS.get(tournament, LEAGUE_IDS["ucl"])
    code, data = await _get("/fixtures", {"league": cfg["league"], "season": cfg["season"]})
    if code != 200 or not data:
        return []
    return [_parse_fixture(f) for f in (data.get("response") or [])]


def _parse_fixture(f: dict) -> dict:
    fixture = f.get("fixture") or {}
    teams   = f.get("teams")   or {}
    goals   = f.get("goals")   or {}
    league  = f.get("league")  or {}
    home    = teams.get("home") or {}
    away    = teams.get("away") or {}
    status  = fixture.get("status") or {}

    ss = str(status.get("short") or "").upper()
    if ss in ("FT", "AET", "PEN"):
        match_status = "final"
    elif ss in ("1H", "HT", "2H", "ET", "P", "LIVE", "BT"):
        match_status = "in_progress"
    else:
        match_status = "scheduled"

    ts = fixture.get("timestamp") or 0
    if ts:
        dt       = datetime.fromtimestamp(int(ts))
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
    else:
        raw      = str(fixture.get("date") or "")
        date_str = raw[:10]
        time_str = raw[11:16]

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
        "kickoff_timestamp": int(ts),
        "tournament":        league.get("name", ""),
        "round":             league.get("round", ""),
    }


# ── 2. Single match ───────────────────────────────────────────────────────────

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
    for i, sd in enumerate(sides):
        side    = "home" if i == 0 else "away"
        team    = sd.get("team") or {}
        team_id = str(team.get("id", ""))
        result[f"{side}_team_id"] = team_id

        for pe in (sd.get("startXI") or []):
            p   = pe.get("player") or {}
            pid = str(p.get("id", ""))
            entry = {"name": p.get("name",""), "player_id": pid,
                     "team_id": team_id, "side": side,
                     "position": p.get("pos",""), "number": str(p.get("number",""))}
            result[f"{side}_starters"].append(entry)
            if pid:
                result["starter_ids"].add(pid)
                result["played_ids"].add(pid)

        for pe in (sd.get("substitutes") or []):
            p   = pe.get("player") or {}
            pid = str(p.get("id", ""))
            result[f"{side}_subs"].append(
                {"name": p.get("name",""), "player_id": pid,
                 "team_id": team_id, "side": side}
            )

    return result


# ── 4. Player stats ───────────────────────────────────────────────────────────

async def get_player_stats(fixture_id: str) -> dict | None:
    code, data = await _get("/fixtures/players", {"fixture": fixture_id})
    if code != 200 or not data:
        return None

    result = {}
    for td in (data.get("response") or []):
        team_id = str((td.get("team") or {}).get("id", ""))
        for pe in (td.get("players") or []):
            p     = pe.get("player") or {}
            stats = (pe.get("statistics") or [{}])[0]
            pid   = str(p.get("id", ""))
            name  = p.get("name", "")

            games    = stats.get("games")    or {}
            goals_s  = stats.get("goals")    or {}
            cards_s  = stats.get("cards")    or {}
            tackles_s= stats.get("tackles")  or {}
            penalty_s= stats.get("penalty")  or {}

            minutes = int(games.get("minutes") or 0)

            entry = {
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
            if pid:   result[pid]          = entry
            if name:  result[name.lower()] = entry

    return result


# ── 5. Events ─────────────────────────────────────────────────────────────────

async def get_match_events(fixture_id: str) -> list[dict]:
    code, data = await _get("/fixtures/events", {"fixture": fixture_id})
    if code != 200 or not data:
        return []

    events = []
    for e in (data.get("response") or []):
        et  = str(e.get("type") or "").lower()
        det = str(e.get("detail") or "").lower()
        pl  = e.get("player") or {}
        as_ = e.get("assist") or {}
        tm  = e.get("team") or {}
        min_= str((e.get("time") or {}).get("elapsed") or "")

        if et == "goal":
            etype = "own_goal" if "own" in det else "goal"
        elif et == "card":
            if "yellow" in det and "red" in det: etype = "yellow_then_red"
            elif "red" in det:                   etype = "red_card"
            else:                                etype = "yellow_card"
        elif et == "subst":
            etype = "substitution"
        else:
            continue

        events.append({
            "type":   etype,
            "minute": min_,
            "player": pl.get("name", ""),
            "assist": as_.get("name", ""),
            "team":   tm.get("name", ""),
        })
    return events


# ── 6. Full match fetch ────────────────────────────────────────────────────────

async def fetch_full_match(fixture_id: str) -> dict | None:
    details = await get_match_details(fixture_id)
    if not details:
        return None
    lineups      = await get_lineups(fixture_id)
    player_stats = await get_player_stats(fixture_id)
    events       = await get_match_events(fixture_id)

    details["lineups"]      = lineups
    details["player_stats"] = player_stats or {}
    details["events"]       = events
    details["played_ids"]   = lineups.get("played_ids", set())
    details["starter_ids"]  = lineups.get("starter_ids", set())
    return details
