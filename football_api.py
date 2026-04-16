"""
football_api.py — FlashScore API (flashscore4.p.rapidapi.com)

Confirmed endpoints:
  GET /api/flashscore/v2/matches/details?match_id=X
  GET /api/flashscore/v2/matches/match/player-stats?match_id=X

No listing endpoint available — admin adds match IDs manually via /addmatch.
Match IDs come from flashscore.com URLs:
  https://www.flashscore.com/match/AbCdEfGh/ → match_id = AbCdEfGh
"""
import logging
import aiohttp
import config

logger = logging.getLogger(__name__)

BASE    = "https://flashscore4.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-host": "flashscore4.p.rapidapi.com",
    "x-rapidapi-key":  config.API_FOOTBALL_KEY,
    "Content-Type":    "application/json",
}


async def _get(endpoint: str, params: dict = None) -> tuple[int, dict | None]:
    url = f"{BASE}/{endpoint.lstrip('/')}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=HEADERS, params=params,
                             timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return 200, await resp.json()
                return resp.status, None
    except Exception as e:
        logger.error("API error (%s): %s", endpoint, e)
        return 0, None


# ── Match details ─────────────────────────────────────────────────────────────

async def get_match_details(match_id: str) -> dict | None:
    code, raw = await _get("/api/flashscore/v2/matches/details", {"match_id": match_id})
    if code != 200 or not raw:
        logger.error("get_match_details HTTP %s for %s", code, match_id)
        return None
    return _parse_match_details(match_id, raw)


def _parse_match_details(match_id: str, raw: dict) -> dict:
    # Teams — FlashScore structure confirmed: raw.home_team.name
    home = raw.get("home_team") or {}
    away = raw.get("away_team") or {}
    home_team = home.get("name") or home.get("short_name") or "?"
    away_team = away.get("name") or away.get("short_name") or "?"

    # Score — try multiple field locations
    def _score(side: str) -> int:
        val = raw.get(f"{side}_score")
        if isinstance(val, dict):
            return int(float(val.get("current") or val.get("normal_time") or 0))
        if val is not None:
            return int(float(val or 0))
        # Some responses nest under "result"
        result = raw.get("result") or {}
        return int(float(result.get(f"{side}_team") or result.get(side) or 0))

    home_score = _score("home")
    away_score = _score("away")

    # Status — confirmed: raw.match_status.is_finished
    ms = raw.get("match_status") or {}
    if ms.get("is_finished"):
        status = "final"
    elif ms.get("is_in_progress"):
        status = "in_progress"
    elif ms.get("is_started"):
        status = "in_progress"
    else:
        status = "scheduled"

    # Date from Unix timestamp
    ts = raw.get("timestamp")
    if ts:
        from datetime import datetime, timezone
        date_str = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    else:
        date_str = ""

    return {
        "id":            match_id,
        "home_team":     home_team,
        "away_team":     away_team,
        "home_score":    home_score,
        "away_score":    away_score,
        "status":        status,
        "date":          date_str,
        "events":        [],   # filled by get_match_incidents if available
        "home_team_id":  home.get("team_id", ""),
        "away_team_id":  away.get("team_id", ""),
        "tournament":    (raw.get("tournament") or {}).get("name", ""),
    }


# ── Player stats ──────────────────────────────────────────────────────────────

async def get_player_stats(match_id: str) -> dict | None:
    code, raw = await _get("/api/flashscore/v2/matches/match/player-stats",
                           {"match_id": match_id})
    if code != 200 or not raw:
        logger.error("get_player_stats HTTP %s for %s", code, match_id)
        return None
    return _parse_player_stats(raw)


def _parse_player_stats(raw: dict) -> dict:
    """
    Confirmed structure:
    {"players": [{
        "name": "Nyland Orjan",
        "team_id": "h8oAv4Ts",
        "position": "Goalkeeper",
        "is_goalkeeper": true,
        "in_base_lineup": true,
        "stats": {
            "CARDS_YELLOW":           {"raw_value": "0"},
            "CARDS_RED":              {"raw_value": "0"},
            "ASSISTS_GOAL":           {"raw_value": "0"},
            "PENALTIES_NOT_CONVERTED":{"raw_value": "0"},
            "GOALS_PENALTY":          {"raw_value": "0"},
            ...
        }
    }]}
    """
    players_raw = raw.get("players") or []
    result = {}

    for p in players_raw:
        name = (p.get("name") or "").strip()
        if not name:
            continue

        stats_raw = p.get("stats") or {}

        def sv(key: str) -> int:
            """Get integer value from ALL_CAPS stat key."""
            entry = stats_raw.get(key)
            if isinstance(entry, dict):
                v = entry.get("raw_value") or entry.get("value") or 0
            else:
                v = entry or 0
            try:
                return int(float(v))
            except Exception:
                return 0

        # Goals: try multiple possible key names
        goals = (sv("GOALS_SCORED") or sv("GOALS") or sv("GOAL") or
                 sv("GOALS_OPEN_PLAY") + sv("GOALS_PENALTY") +
                 sv("GOALS_OWN"))  # own goals don't count for player

        # Exclude own goals from goals count
        goals = max(0, goals - sv("GOALS_OWN"))

        # Minutes
        minutes = sv("MINUTES_PLAYED") or sv("MINUTES") or (
            90 if p.get("in_base_lineup") else 0
        )

        result[name.lower()] = {
            "name":           name,
            "team_id":        p.get("team_id", ""),
            "position":       p.get("position", ""),
            "is_goalkeeper":  bool(p.get("is_goalkeeper")),
            "in_lineup":      bool(p.get("in_base_lineup")),
            "goals":          goals,
            "assists":        sv("ASSISTS_GOAL") or sv("ASSISTS"),
            "yellow_cards":   sv("CARDS_YELLOW"),
            "red_cards":      sv("CARDS_RED"),
            "penalty_miss":   sv("PENALTIES_NOT_CONVERTED"),
            "minutes_played": minutes,
            "goals_conceded": 0,    # filled by scheduler from match score
            "clean_sheet":    False, # filled by scheduler
            "raw_stats":      {k: sv(k) for k in stats_raw},
        }

    return result


# ── Match incidents (goals/cards timeline) ────────────────────────────────────

async def get_match_incidents(match_id: str) -> list[dict]:
    """Try to get goal/card events. Returns [] if endpoint doesn't exist."""
    for ep in [
        "/api/flashscore/v2/matches/match/incidents",
        "/api/flashscore/v2/matches/incidents",
    ]:
        code, raw = await _get(ep, {"match_id": match_id})
        if code == 200 and raw:
            return _parse_incidents(raw)
    return []


def _parse_incidents(raw: dict) -> list[dict]:
    incidents = raw.get("incidents") or raw.get("events") or (
        raw if isinstance(raw, list) else []
    )
    events = []
    for inc in incidents:
        itype = str(inc.get("incident_type") or inc.get("type") or "").lower()
        if "goal" in itype:
            t = "goal"
        elif "yellow" in itype:
            t = "yellow_card"
        elif "red" in itype:
            t = "red_card"
        elif "penalty" in itype and "miss" in itype:
            t = "penalty_miss"
        else:
            continue

        player = (inc.get("player", {}).get("name") if isinstance(inc.get("player"), dict)
                  else inc.get("player") or inc.get("player_name") or "")
        assist = (inc.get("assist", {}).get("name") if isinstance(inc.get("assist"), dict)
                  else inc.get("assist") or "")
        is_home = inc.get("is_home") or inc.get("home")
        team = "home" if str(is_home).lower() in ("true", "1") else "away"
        minute = str(inc.get("time") or inc.get("minute") or inc.get("incident_time") or "")

        events.append({"type": t, "minute": minute,
                        "player": player, "assist": assist, "team": team})
    return events


# ── Full match fetch (details + stats + incidents) ────────────────────────────

async def fetch_full_match(match_id: str) -> dict | None:
    """
    Fetch everything about a match in one call.
    Returns enriched match dict ready for save_match_cache.
    """
    details = await get_match_details(match_id)
    if not details:
        return None

    stats   = await get_player_stats(match_id)
    events  = await get_match_incidents(match_id)

    details["player_stats"] = stats or {}
    details["events"]       = events

    return details
