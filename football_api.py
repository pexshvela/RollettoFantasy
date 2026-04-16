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

    # Score — confirmed: raw["scores"]["home"] and raw["scores"]["away"]
    scores = raw.get("scores") or {}
    home_score = int(float(scores.get("home") or scores.get("home_total") or 0))
    away_score = int(float(scores.get("away") or scores.get("away_total") or 0))

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
            """Get integer value from ALL_CAPS FlashScore stat key."""
            entry = stats_raw.get(key)
            if isinstance(entry, dict):
                v = entry.get("raw_value") or entry.get("value") or 0
            else:
                v = entry or 0
            try:
                return int(float(v))
            except Exception:
                return 0

        # Goals: regular + penalty goals, exclude own goals
        goals_open   = sv("GOALS_OPEN_PLAY") or sv("GOALS_SCORED") or sv("GOALS")
        goals_penalty= sv("GOALS_PENALTY")
        own_goals    = sv("GOALS_OWN") or sv("OWN_GOALS")
        goals = max(0, goals_open + goals_penalty - own_goals)

        # Minutes — use MINUTES_PLAYED or assume 90 if in starting lineup
        minutes = sv("MINUTES_PLAYED") or sv("MINUTES")
        if not minutes and p.get("in_base_lineup"):
            minutes = 90

        # Defensive actions for the +1 per 3 rule
        tackles       = sv("TACKLES") or sv("TACKLE_TOTAL") or sv("TACKLES_WON")
        interceptions = sv("INTERCEPTIONS") or sv("INTERCEPTION")
        blocks        = sv("BLOCKED_SHOTS") or sv("CLEARANCES") or sv("BLOCKS")

        result[name.lower()] = {
            "name":             name,
            "team_id":          p.get("team_id", ""),
            "position":         p.get("position", ""),
            "is_goalkeeper":    bool(p.get("is_goalkeeper")),
            "in_lineup":        bool(p.get("in_base_lineup")),
            "goals":            goals,
            "own_goals":        own_goals,
            "assists":          sv("ASSISTS_GOAL") or sv("ASSISTS"),
            "yellow_cards":     sv("CARDS_YELLOW"),
            "red_cards":        sv("CARDS_RED"),
            "yellow_then_red":  sv("CARDS_YELLOW_RED"),
            "penalty_miss":     sv("PENALTIES_NOT_CONVERTED"),
            "penalty_earned":   sv("PENALTIES_WON"),
            "penalty_conceded": sv("PENALTIES_COMMITTED") or sv("PENALTIES_CONCEDED"),
            "penalty_saved":    sv("PENALTIES_SAVED"),
            "saves":            sv("SAVES") or sv("GOALKEEPER_SAVES") or sv("SHOTS_SAVED_TOTAL"),
            "tackles":          tackles,
            "interceptions":    interceptions,
            "blocks":           blocks,
            "minutes_played":   minutes,
            "goals_conceded":   0,     # filled by scheduler
            "clean_sheet":      False, # filled by scheduler
            "raw_stats":        {k: sv(k) for k in stats_raw},
        }

    return result


# ── Match incidents (goals/cards timeline) ────────────────────────────────────

async def get_match_incidents(match_id: str) -> list[dict]:
    """
    Confirmed endpoint: /api/flashscore/v2/matches/match/summary
    Returns list of events: [{minutes, team, description, players:[{name, type}]}]
    """
    code, raw = await _get("/api/flashscore/v2/matches/match/summary",
                           {"match_id": match_id})
    if code == 200 and raw:
        return _parse_summary(raw)
    return []


def _parse_summary(raw) -> list[dict]:
    """
    Confirmed structure (list of events):
    [{"minutes": "1", "team": "away", "description": "GOAL!...",
      "players": [{"name": "Guler A.", "type": "Goal"}]}]
    """
    if isinstance(raw, dict):
        items = raw.get("incidents") or raw.get("events") or raw.get("summary") or []
    else:
        items = raw if isinstance(raw, list) else []

    events = []
    for inc in items:
        desc = str(inc.get("description") or "").lower()
        players = inc.get("players") or []
        minute = str(inc.get("minutes") or inc.get("minute") or "")
        team = str(inc.get("team") or "").lower()  # "home" or "away"

        # Determine event type from players list or description
        for player_entry in players:
            ptype = str(player_entry.get("type") or "").lower()
            pname = player_entry.get("name") or ""

            if ptype == "goal" or "goal" in ptype:
                etype = "goal"
            elif "yellow" in ptype or "yellow" in desc:
                etype = "yellow_card"
            elif "red" in ptype or ("red" in desc and "yellow" not in desc):
                etype = "red_card"
            elif "penalty" in ptype and "miss" in ptype:
                etype = "penalty_miss"
            else:
                continue

            # Assist: second player in list if type is Assist
            assist = ""
            for other in players:
                if str(other.get("type") or "").lower() in ("assist", "goal assist"):
                    assist = other.get("name") or ""
                    break

            events.append({
                "type":   etype,
                "minute": minute,
                "player": pname,
                "assist": assist,
                "team":   team,
            })
            break  # one event per incident entry

        # If no players list but description mentions goal/card
        if not players:
            if "goal" in desc:
                events.append({"type": "goal", "minute": minute,
                                "player": "", "assist": "", "team": team})
            elif "yellow" in desc:
                events.append({"type": "yellow_card", "minute": minute,
                                "player": "", "assist": "", "team": team})
            elif "red card" in desc:
                events.append({"type": "red_card", "minute": minute,
                                "player": "", "assist": "", "team": team})

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
