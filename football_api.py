"""
football_api.py — FlashScore API wrapper
Host: flashscore4.p.rapidapi.com
Two confirmed endpoints:
  GET /api/flashscore/v2/matches/details?match_id=X
  GET /api/flashscore/v2/matches/match/player-stats?match_id=X

For listing UCL matches we probe several endpoints — use /testflash in bot to discover.
"""
import logging
import aiohttp
import config

logger = logging.getLogger(__name__)

BASE   = "https://flashscore4.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-host": "flashscore4.p.rapidapi.com",
    "x-rapidapi-key":  config.API_FOOTBALL_KEY,
    "Content-Type": "application/json",
}

# UCL tournament ID on FlashScore — discovered via /testflash_search
# Update this after running /testflash_search in the bot
UCL_TOURNAMENT_ID = ""   # fill after discovery
UCL_SEASON_ID     = ""   # fill after discovery


async def _get(endpoint: str, params: dict = None) -> tuple[int, dict | list | None]:
    """Return (http_status, parsed_json)."""
    url = f"{BASE}/{endpoint.lstrip('/')}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=HEADERS, params=params,
                             timeout=aiohttp.ClientTimeout(total=15)) as resp:
                status = resp.status
                if status == 200:
                    return status, await resp.json()
                return status, None
    except Exception as e:
        logger.error("FlashScore API error (%s): %s", endpoint, e)
        return 0, None


# ── Match details ─────────────────────────────────────────────────────────────

async def get_match_details(match_id: str) -> dict | None:
    """
    Returns normalized match dict:
    {id, home_team, away_team, home_score, away_score, status, date, events}
    events: [{type, minute, player, team, assist}]
    """
    status, data = await _get(
        "/api/flashscore/v2/matches/details",
        {"match_id": match_id}
    )
    if not data:
        logger.error("get_match_details HTTP %s for %s", status, match_id)
        return None
    return _parse_match_details(match_id, data)


def _parse_match_details(match_id: str, raw: dict) -> dict:
    """Flexible parser — handles multiple possible response structures."""
    # Try common nesting patterns
    m = (raw.get("match") or raw.get("event") or
         raw.get("data", {}).get("match") or raw)

    # Teams
    home_team = (_nested(m, "homeTeam", "name") or
                 _nested(m, "home", "name") or
                 _nested(m, "teams", "home", "name") or "?")
    away_team = (_nested(m, "awayTeam", "name") or
                 _nested(m, "away", "name") or
                 _nested(m, "teams", "away", "name") or "?")

    # Scores
    home_score = int(_nested(m, "homeScore", "current") or
                     _nested(m, "homeScore") or
                     _nested(m, "score", "home") or 0)
    away_score = int(_nested(m, "awayScore", "current") or
                     _nested(m, "awayScore") or
                     _nested(m, "score", "away") or 0)

    # Status
    raw_status = str(
        _nested(m, "status", "type") or
        _nested(m, "status", "description") or
        _nested(m, "status") or
        m.get("statusType") or ""
    ).lower()
    if any(x in raw_status for x in ["finish", "final", "ft", "ended", "complete"]):
        status = "final"
    elif any(x in raw_status for x in ["progress", "live", "playing", "half"]):
        status = "in_progress"
    else:
        status = "scheduled"

    # Date
    import datetime
    ts = m.get("startTimestamp") or m.get("timestamp") or m.get("date")
    if ts and str(ts).isdigit():
        date_str = datetime.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    else:
        date_str = str(ts or "")[:10]

    # Events (goals, cards)
    raw_events = (m.get("incidents") or m.get("events") or
                  m.get("timeline") or [])
    events = _parse_events(raw_events)

    return {
        "id":         match_id,
        "home_team":  home_team,
        "away_team":  away_team,
        "home_score": home_score,
        "away_score": away_score,
        "status":     status,
        "date":       date_str,
        "events":     events,
        "raw":        raw,   # kept for debugging
    }


def _parse_events(raw_events: list) -> list:
    events = []
    for e in raw_events:
        etype = str(
            e.get("incidentType") or e.get("type") or e.get("eventType") or ""
        ).lower()

        if any(x in etype for x in ["goal", "score"]):
            t = "goal"
        elif "yellow" in etype or etype == "card":
            t = "yellow_card"
        elif "red" in etype:
            t = "red_card"
        elif "penalty" in etype and "miss" in etype:
            t = "penalty_miss"
        else:
            continue

        # Player name — try several field paths
        player = (e.get("player", {}).get("name") if isinstance(e.get("player"), dict)
                  else e.get("player") or e.get("playerName") or
                  _nested(e, "player1", "name") or "")

        assist = (e.get("assist", {}).get("name") if isinstance(e.get("assist"), dict)
                  else e.get("assist") or e.get("assistName") or "")

        team_side = str(e.get("isHome") or e.get("team") or "").lower()
        team = "home" if team_side in ("true", "1", "home") else "away"

        minute = str(e.get("time") or e.get("minute") or e.get("incidentTime") or "")

        events.append({
            "type": t, "minute": minute,
            "player": player, "assist": assist, "team": team,
        })
    return events


# ── Player stats ──────────────────────────────────────────────────────────────

async def get_player_stats(match_id: str) -> dict | None:
    """
    Returns {player_name_lower: stats_dict} for all players in the match.
    stats_dict keys: goals, assists, yellow_cards, red_cards,
                     penalty_miss, minutes_played, goals_conceded
    """
    status, data = await _get(
        "/api/flashscore/v2/matches/match/player-stats",
        {"match_id": match_id}
    )
    if not data:
        logger.error("get_player_stats HTTP %s for %s", status, match_id)
        return None
    return _parse_player_stats(data)


def _parse_player_stats(raw: dict) -> dict:
    result = {}

    # Try to find player lists for home and away
    home_players = (
        _nested(raw, "homeTeam", "players") or
        _nested(raw, "home", "players") or
        _nested(raw, "data", "home", "players") or
        _nested(raw, "response", "home", "players") or []
    )
    away_players = (
        _nested(raw, "awayTeam", "players") or
        _nested(raw, "away", "players") or
        _nested(raw, "data", "away", "players") or
        _nested(raw, "response", "away", "players") or []
    )

    # Also try flat list
    all_players = home_players + away_players
    if not all_players:
        flat = raw.get("players") or raw.get("data") or []
        if isinstance(flat, list):
            all_players = flat

    for p in all_players:
        name = (p.get("name") or p.get("playerName") or
                _nested(p, "player", "name") or "").strip()
        if not name:
            continue

        stats_raw = p.get("stats") or p.get("statistics") or p.get("playerStats") or {}

        # stats can be list of {name, value} or a dict
        if isinstance(stats_raw, list):
            stats = {}
            for s in stats_raw:
                k = str(s.get("name") or s.get("key") or "").lower().replace(" ", "_")
                v = s.get("value") or s.get("displayValue") or 0
                try:
                    stats[k] = int(float(v))
                except Exception:
                    stats[k] = 0
        else:
            stats = {k.lower().replace(" ", "_"): _safe_int(v)
                     for k, v in stats_raw.items()}

        result[name.lower()] = {
            "name":           name,
            "goals":          stats.get("goals") or stats.get("goal") or 0,
            "assists":        stats.get("assists") or stats.get("assist") or 0,
            "yellow_cards":   stats.get("yellow_cards") or stats.get("yellowcard") or stats.get("yellow") or 0,
            "red_cards":      stats.get("red_cards") or stats.get("redcard") or stats.get("red") or 0,
            "penalty_miss":   stats.get("penalty_miss") or stats.get("penaltymissed") or 0,
            "minutes_played": stats.get("minutes_played") or stats.get("minutesplayed") or stats.get("time_played") or 90,
            "goals_conceded": stats.get("goals_conceded") or stats.get("goalsconceded") or 0,
            "raw_stats":      stats,
        }

    return result


# ── Match listing ─────────────────────────────────────────────────────────────

async def get_ucl_matches(days_back: int = 2) -> list[dict]:
    """
    Try several endpoints to get recent UCL matches.
    Returns list of {id, home_team, away_team, home_score, away_score, status, date}
    """
    from datetime import date, timedelta
    today = date.today()

    # Endpoints to try in order
    attempts = [
        ("/api/flashscore/v2/category/tournament/matches",
         {"tournament_id": UCL_TOURNAMENT_ID, "season_id": UCL_SEASON_ID}),
        ("/api/flashscore/v2/matches",
         {"tournament_id": UCL_TOURNAMENT_ID}),
        ("/api/flashscore/v2/tournament/matches",
         {"tournament_id": UCL_TOURNAMENT_ID}),
    ]

    for endpoint, params in attempts:
        if not UCL_TOURNAMENT_ID:
            break  # need to discover ID first
        code, data = await _get(endpoint, params)
        if code == 200 and data:
            return _extract_match_list(data, today, days_back)

    # Fallback: try date-based endpoints
    matches = []
    for i in range(days_back + 1):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        for ep in [f"/api/flashscore/v2/matches/{d}",
                   f"/api/flashscore/v2/matches",
                   f"/api/flashscore/v2/livescore"]:
            code, data = await _get(ep, {"date": d, "sport": "football"})
            if code == 200 and data:
                found = _extract_match_list(data, today, days_back, ucl_only=True)
                matches.extend(found)
                break

    return matches


def _extract_match_list(data, today, days_back: int, ucl_only: bool = False) -> list:
    from datetime import timedelta
    cutoff = (today - timedelta(days=days_back)).isoformat()

    raw_list = (data.get("events") or data.get("matches") or
                data.get("data") or (data if isinstance(data, list) else []))

    results = []
    UCL_KEYWORDS = {"champions league", "ucl", "uefa cl"}

    for m in raw_list:
        # Filter to UCL if needed
        if ucl_only:
            tournament = str(
                _nested(m, "tournament", "name") or
                _nested(m, "competition", "name") or
                m.get("league", "") or ""
            ).lower()
            if not any(kw in tournament for kw in UCL_KEYWORDS):
                continue

        match_id = str(m.get("id") or m.get("matchId") or m.get("eventId") or "")
        if not match_id:
            continue

        parsed = _parse_match_details(match_id, {"match": m})
        if parsed["date"] >= cutoff:
            results.append(parsed)

    return results


# ── Discovery helpers (for /testflash_search) ─────────────────────────────────

async def discover_ucl_id() -> dict:
    """Try to find UCL tournament ID. Returns raw responses for inspection."""
    results = {}
    for ep, params in [
        ("/api/flashscore/v2/search", {"q": "champions league"}),
        ("/api/flashscore/v2/category/search", {"name": "champions league"}),
        ("/api/flashscore/v2/tournaments", {"category": "football"}),
        ("/api/flashscore/v2/sports/football/tournaments", {}),
    ]:
        code, data = await _get(ep, params)
        results[ep] = {"status": code, "preview": str(data)[:300] if data else None}
    return results


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nested(d: dict, *keys):
    """Safely navigate nested dict."""
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return None
    return cur


def _safe_int(val) -> int:
    try:
        return int(float(val or 0))
    except Exception:
        return 0
