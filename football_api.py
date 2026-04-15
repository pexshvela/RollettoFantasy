"""
football_api.py — UCL RapidAPI integration (ESPN-based)
Base URL: https://uefa-champions-league1.p.rapidapi.com
"""
import logging
import asyncio
import aiohttp
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)

BASE_URL = "https://uefa-champions-league1.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-host": "uefa-champions-league1.p.rapidapi.com",
    "x-rapidapi-key": config.API_FOOTBALL_KEY,
}

# UCL team names as returned by the API — must match exactly
UCL_TEAMS = {
    "Arsenal", "Bayern München", "Barcelona", "Liverpool",
    "Paris Saint-Germain", "Inter", "Manchester City", "Real Madrid",
    "Sporting CP", "Atlético de Madrid",
}


async def _get(session: aiohttp.ClientSession, endpoint: str, params: dict = None) -> dict | None:
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    try:
        async with session.get(url, headers=HEADERS, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                logger.error("API %s returned %s", endpoint, resp.status)
                return None
    except Exception as e:
        logger.error("API request error (%s): %s", endpoint, e)
        return None


async def get_scores() -> list[dict]:
    """
    Fetch recent/live UCL match scores.
    Returns list of match dicts with keys:
      id, status, date, homeTeam, awayTeam, homeScore, awayScore, events
    """
    async with aiohttp.ClientSession() as session:
        data = await _get(session, "/scores")
        if not data:
            return []

        matches = []
        # ESPN API typically returns {"events": [...]} or a list directly
        raw = data.get("events") or data.get("matches") or (data if isinstance(data, list) else [])

        for m in raw:
            try:
                status = _extract_status(m)
                home = _extract_team(m, "home")
                away = _extract_team(m, "away")
                matches.append({
                    "id": str(m.get("id", "")),
                    "status": status,  # "final", "in_progress", "scheduled"
                    "date": m.get("date", ""),
                    "homeTeam": home["name"],
                    "awayTeam": away["name"],
                    "homeScore": home["score"],
                    "awayScore": away["score"],
                    "raw": m,  # Keep raw for detailed parsing
                })
            except Exception as e:
                logger.warning("Failed to parse match: %s", e)
                continue

        logger.info("Fetched %d UCL matches", len(matches))
        return matches


async def get_player_match_stats(player_espn_id: int, match_date: str) -> dict | None:
    """
    Get a player's stats for a specific match date.
    match_date format: "YYYY-MM-DD"
    Returns dict with: goals, assists, yellow_cards, red_cards, 
                       penalty_miss, clean_sheet, minutes_played
    """
    async with aiohttp.ClientSession() as session:
        data = await _get(session, "/athlete/eventlog", {"playerId": str(player_espn_id)})
        if not data:
            return None

        events = (data.get("events") or data.get("eventlog") or
                  data.get("athlete", {}).get("eventLog", {}).get("events", []) or [])

        # Find the event matching our match date
        for event in events:
            event_date = _extract_event_date(event)
            if event_date and event_date.startswith(match_date):
                return _parse_player_event_stats(event)

        return None


async def get_match_events(match_id: str) -> list[dict]:
    """
    Get goal/card events for a specific match.
    Returns list of {type, player_name, team, minute, assist_name}
    """
    async with aiohttp.ClientSession() as session:
        data = await _get(session, "/scores", {"event": match_id})
        if not data:
            return []

        raw = data.get("events") or (data if isinstance(data, list) else [])
        events = []
        for m in raw:
            if str(m.get("id", "")) == str(match_id):
                return _extract_match_events(m)
        return events


# ── Internal parsers ──────────────────────────────────────────────────────────

def _extract_status(match: dict) -> str:
    """Normalize match status to 'final' | 'in_progress' | 'scheduled'."""
    status = (
        match.get("status", {}).get("type", {}).get("name", "")
        or match.get("status", {}).get("description", "")
        or match.get("statusType", "")
        or ""
    ).lower()

    if any(s in status for s in ["final", "ft", "finished", "complete", "full-time"]):
        return "final"
    elif any(s in status for s in ["in_progress", "in progress", "live", "halftime"]):
        return "in_progress"
    return "scheduled"


def _extract_team(match: dict, side: str) -> dict:
    """Extract team name and score from match dict."""
    competitors = match.get("competitions", [{}])[0].get("competitors", []) if match.get("competitions") else []
    for c in competitors:
        home_away = c.get("homeAway", "").lower()
        if home_away == side:
            return {
                "name": c.get("team", {}).get("displayName", c.get("team", {}).get("name", "Unknown")),
                "score": int(c.get("score", 0) or 0),
            }
    # Fallback for simpler response structures
    if side == "home":
        return {"name": match.get("homeTeam", {}).get("name", "?"), "score": int(match.get("homeScore", 0) or 0)}
    return {"name": match.get("awayTeam", {}).get("name", "?"), "score": int(match.get("awayScore", 0) or 0)}


def _extract_event_date(event: dict) -> str:
    """Extract date string from player event entry."""
    date = (
        event.get("date")
        or event.get("gameDate")
        or event.get("atDate")
        or event.get("event", {}).get("date", "")
    )
    if date:
        return str(date)[:10]  # YYYY-MM-DD
    return ""


def _parse_player_event_stats(event: dict) -> dict:
    """Parse a player's event log entry into stats we need for points."""
    stats_raw = (
        event.get("stats")
        or event.get("statistics")
        or event.get("athlete", {}).get("stats", [])
        or []
    )

    stats = {}
    if isinstance(stats_raw, list):
        for s in stats_raw:
            name = s.get("name") or s.get("abbreviation") or ""
            val = s.get("value") or s.get("displayValue") or "0"
            try:
                stats[name.lower()] = int(float(val))
            except Exception:
                stats[name.lower()] = 0
    elif isinstance(stats_raw, dict):
        for k, v in stats_raw.items():
            try:
                stats[k.lower()] = int(float(v or 0))
            except Exception:
                stats[k.lower()] = 0

    return {
        "goals":          stats.get("goals") or stats.get("totalgoals") or stats.get("g") or 0,
        "assists":        stats.get("assists") or stats.get("goalassists") or stats.get("a") or 0,
        "yellow_cards":   stats.get("yellowcards") or stats.get("yc") or stats.get("foulscommitted") and 0 or 0,
        "red_cards":      stats.get("redcards") or stats.get("rc") or 0,
        "penalty_miss":   stats.get("penaltymiss") or stats.get("penaltiesmissed") or 0,
        "minutes_played": stats.get("minutesplayed") or stats.get("mp") or stats.get("min") or 90,
        "goals_conceded": stats.get("goalsconceded") or stats.get("gc") or 0,
        "saves":          stats.get("saves") or stats.get("goalssaved") or 0,
        "raw_stats":      stats,  # Keep for debugging
    }


def _extract_match_events(match: dict) -> list[dict]:
    """Extract goal/card play-by-play events from match data."""
    events = []
    competitions = match.get("competitions", [{}])
    if not competitions:
        return events
    details = competitions[0].get("details", [])
    for d in details:
        etype = d.get("type", {}).get("text", "").lower()
        if "goal" in etype or "card" in etype:
            events.append({
                "type": etype,
                "player_name": d.get("athletesInvolved", [{}])[0].get("displayName", ""),
                "minute": d.get("clock", {}).get("displayValue", ""),
            })
    return events
