"""
football_api.py — FlashScore API (flashscore4.p.rapidapi.com)

Confirmed endpoints used:
  #2  GET /matches/list-by-date   → list all matches on a date, filter UCL by tournament_url
  #3  GET /matches/details        → score, status, teams, team_ids
  #4  GET /matches/match/summary  → goals, cards, assists (events)
  #6  GET /matches/match/lineups  → who started (predictedLineups) and who was on bench
  #7  GET /matches/match/player-stats → per-player stats (goals, assists, cards, saves etc.)
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

UCL_URL_KEYWORDS = ["champions-league", "champions_league", "ucl"]


async def _get(endpoint: str, params: dict = None) -> tuple[int, any]:
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


# ── 1. List UCL matches by date ───────────────────────────────────────────────

async def get_ucl_matches_by_date(date_str: str) -> list[dict]:
    """
    Use /list-by-date to get all football matches on a date,
    then filter to UCL only by tournament_url containing 'champions-league'.
    date_str: 'YYYY-MM-DD'
    Returns list of normalized match dicts.
    """
    code, data = await _get(
        "/api/flashscore/v2/matches/list-by-date",
        {"sport_id": "1", "date": date_str, "timezone": "Europe/Berlin"}
    )
    if code != 200 or not data:
        logger.error("list-by-date HTTP %s for %s", code, date_str)
        return []

    tournaments = data if isinstance(data, list) else data.get("tournaments", [])
    ucl_matches = []

    for tournament in tournaments:
        t_url = str(tournament.get("tournament_url") or "").lower()
        t_name = str(tournament.get("name") or "").lower()

        is_ucl = (
            any(kw in t_url for kw in UCL_URL_KEYWORDS) or
            "champions" in t_name
        )
        if not is_ucl:
            continue

        for m in (tournament.get("matches") or []):
            mid = m.get("match_id", "")
            if not mid:
                continue

            ms = m.get("match_status") or {}
            if ms.get("is_finished"):
                status = "final"
            elif ms.get("is_in_progress") or ms.get("is_started"):
                status = "in_progress"
            else:
                status = "scheduled"

            scores = m.get("scores") or {}
            home_team = m.get("home_team") or {}
            away_team = m.get("away_team") or {}

            import datetime
            ts = m.get("timestamp")
            date_out = datetime.datetime.fromtimestamp(int(ts), tz=datetime.timezone.utc).strftime("%Y-%m-%d") if ts else date_str

            ucl_matches.append({
                "id":            mid,
                "home_team":     home_team.get("name", "?"),
                "away_team":     away_team.get("name", "?"),
                "home_score":    int(float(scores.get("home") or 0)),
                "away_score":    int(float(scores.get("away") or 0)),
                "home_team_id":  home_team.get("team_id", ""),
                "away_team_id":  away_team.get("team_id", ""),
                "status":        status,
                "date":          date_out,
                "tournament":    tournament.get("name", ""),
            })

    logger.info("Found %d UCL match(es) on %s", len(ucl_matches), date_str)
    return ucl_matches


# ── 2. Match details (score + status) ────────────────────────────────────────

async def get_match_details(match_id: str) -> dict | None:
    code, raw = await _get("/api/flashscore/v2/matches/details", {"match_id": match_id})
    if code != 200 or not raw:
        logger.error("get_match_details HTTP %s for %s", code, match_id)
        return None
    return _parse_details(match_id, raw)


def _parse_details(match_id: str, raw: dict) -> dict:
    home = raw.get("home_team") or {}
    away = raw.get("away_team") or {}

    # Score confirmed: raw["scores"]["home"] / ["away"]
    scores = raw.get("scores") or {}
    home_score = int(float(scores.get("home") or 0))
    away_score = int(float(scores.get("away") or 0))

    ms = raw.get("match_status") or {}
    if ms.get("is_finished"):
        status = "final"
    elif ms.get("is_in_progress") or ms.get("is_started"):
        status = "in_progress"
    else:
        status = "scheduled"

    import datetime
    ts = raw.get("timestamp")
    date_str = (datetime.datetime.fromtimestamp(int(ts), tz=datetime.timezone.utc).strftime("%Y-%m-%d")
                if ts else "")

    return {
        "id":            match_id,
        "home_team":     home.get("name") or home.get("short_name") or "?",
        "away_team":     away.get("name") or away.get("short_name") or "?",
        "home_score":    home_score,
        "away_score":    away_score,
        "home_team_id":  home.get("team_id", ""),
        "away_team_id":  away.get("team_id", ""),
        "status":        status,
        "date":          date_str,
        "tournament":    (raw.get("tournament") or {}).get("name", ""),
    }


# ── 3. Lineups — who actually played ─────────────────────────────────────────

async def get_lineups(match_id: str) -> dict:
    """
    Returns:
    {
      "home_starters":  [{"name": "Neuer M.", "player_id": "...", "team_id": "..."}],
      "away_starters":  [...],
      "home_subs":      [...],
      "away_subs":      [...],
      "home_team_id":   "...",
      "away_team_id":   "...",
      "starter_ids":    set of player_ids who started,
      "played_ids":     set of player_ids who played (starters + used subs),
    }
    """
    code, raw = await _get("/api/flashscore/v2/matches/match/lineups", {"match_id": match_id})
    if code != 200 or not raw:
        logger.warning("get_lineups HTTP %s for %s", code, match_id)
        return {}

    result = {
        "home_starters": [], "away_starters": [],
        "home_subs": [],     "away_subs": [],
        "home_team_id": "",  "away_team_id": "",
        "starter_ids": set(), "played_ids": set(),
    }

    items = raw if isinstance(raw, list) else [raw]

    for side_data in items:
        side = str(side_data.get("side") or "").lower()  # "home" or "away"
        team_id = str(side_data.get("team_id") or "")

        if side == "home":
            result["home_team_id"] = team_id
        elif side == "away":
            result["away_team_id"] = team_id

        # Starters: predictedLineups (confirmed field from your test)
        starters = side_data.get("predictedLineups") or side_data.get("lineups") or []
        for p in starters:
            entry = {
                "name":       p.get("name") or p.get("fieldName") or "",
                "field_name": p.get("fieldName") or "",
                "player_id":  p.get("player_id") or "",
                "number":     p.get("number") or "",
                "team_id":    team_id,
                "side":       side,
            }
            if side == "home":
                result["home_starters"].append(entry)
            else:
                result["away_starters"].append(entry)
            if entry["player_id"]:
                result["starter_ids"].add(entry["player_id"])
                result["played_ids"].add(entry["player_id"])

        # Substitutes
        subs = side_data.get("substitutes") or side_data.get("bench") or []
        for p in subs:
            entry = {
                "name":       p.get("name") or p.get("fieldName") or "",
                "field_name": p.get("fieldName") or "",
                "player_id":  p.get("player_id") or "",
                "number":     p.get("number") or "",
                "team_id":    team_id,
                "side":       side,
                "came_on":    p.get("came_on") or p.get("substitute_time") or "",
            }
            if side == "home":
                result["home_subs"].append(entry)
            else:
                result["away_subs"].append(entry)
            # Only add to played_ids if they actually came on
            if entry["player_id"] and entry.get("came_on"):
                result["played_ids"].add(entry["player_id"])

    logger.info("Lineups: %d home starters, %d away starters",
                len(result["home_starters"]), len(result["away_starters"]))
    return result


# ── 4. Player stats ───────────────────────────────────────────────────────────

async def get_player_stats(match_id: str) -> dict | None:
    """
    Returns {flashscore_player_id: stats_dict} keyed by FlashScore player_id.
    Also keyed by lowercase name for fallback matching.
    """
    code, raw = await _get("/api/flashscore/v2/matches/match/player-stats",
                           {"match_id": match_id})
    if code != 200 or not raw:
        logger.error("get_player_stats HTTP %s for %s", code, match_id)
        return None
    return _parse_player_stats(raw)


def _parse_player_stats(raw: dict) -> dict:
    players_raw = raw.get("players") or []
    result = {}

    for p in players_raw:
        name       = (p.get("name") or "").strip()
        player_id  = p.get("player_id") or ""
        stats_raw  = p.get("stats") or {}

        def sv(key: str) -> int:
            entry = stats_raw.get(key)
            if isinstance(entry, dict):
                v = entry.get("raw_value") or entry.get("value") or 0
            else:
                v = entry or 0
            try:
                return int(float(v))
            except Exception:
                return 0

        # Goals
        goals_open    = sv("GOALS_OPEN_PLAY")
        goals_penalty = sv("GOALS_PENALTY")
        own_goals     = sv("GOALS_OWN") or sv("OWN_GOALS")
        goals         = max(0, goals_open + goals_penalty - own_goals)

        # Minutes — use explicit field or assume 90 if in base lineup
        minutes = sv("MINUTES_PLAYED") or sv("MINUTES")
        if not minutes and p.get("in_base_lineup"):
            minutes = 90

        # Saves
        saves = (sv("SAVES") or sv("GOALKEEPER_SAVES") or
                 sv("SHOTS_SAVED_TOTAL") or sv("SHOTS_SAVED"))

        # Defensive actions
        tackles        = sv("TACKLES") or sv("TACKLE_TOTAL") or sv("TACKLES_WON")
        interceptions  = sv("INTERCEPTIONS")
        blocks         = sv("BLOCKED_SHOTS") or sv("CLEARANCES") or sv("BLOCKS")

        stats = {
            "name":             name,
            "player_id":        player_id,
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
            "saves":            saves,
            "tackles":          tackles,
            "interceptions":    interceptions,
            "blocks":           blocks,
            "minutes_played":   minutes,
            "goals_conceded":   0,      # set by scheduler
            "clean_sheet":      False,  # set by scheduler
        }

        # Store by both player_id and lowercase name for matching
        if player_id:
            result[player_id] = stats
        if name:
            result[name.lower()] = stats

    return result


# ── 5. Match events (goals/cards) ─────────────────────────────────────────────

async def get_match_incidents(match_id: str) -> list[dict]:
    """
    Confirmed endpoint: /matches/match/summary
    Returns list of goal/card events.
    """
    code, raw = await _get("/api/flashscore/v2/matches/match/summary",
                           {"match_id": match_id})
    if code == 200 and raw:
        return _parse_summary(raw)
    return []


def _parse_summary(raw) -> list[dict]:
    items = raw if isinstance(raw, list) else (
        raw.get("incidents") or raw.get("events") or []
    )
    events = []
    for inc in items:
        desc    = str(inc.get("description") or "").lower()
        players = inc.get("players") or []
        minute  = str(inc.get("minutes") or inc.get("minute") or "")
        team    = str(inc.get("team") or "").lower()

        for player_entry in players:
            ptype = str(player_entry.get("type") or "").lower()
            pname = player_entry.get("name") or ""

            if ptype == "goal" or "goal" in ptype:
                etype = "goal"
            elif "own" in ptype:
                etype = "own_goal"
            elif "yellow" in ptype:
                etype = "yellow_card"
            elif "red" in ptype:
                etype = "red_card"
            elif "penalty" in ptype and "miss" in ptype:
                etype = "penalty_miss"
            else:
                continue

            assist = next(
                (o.get("name") or "" for o in players
                 if str(o.get("type") or "").lower() in ("assist", "goal assist")),
                ""
            )

            events.append({
                "type":   etype,
                "minute": minute,
                "player": pname,
                "assist": assist,
                "team":   team,
            })
            break

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


# ── 6. Full match fetch ────────────────────────────────────────────────────────

async def fetch_full_match(match_id: str) -> dict | None:
    """
    Fetch details + lineups + player_stats + events.
    Returns enriched match dict ready for processing.
    """
    details = await get_match_details(match_id)
    if not details:
        return None

    lineups      = await get_lineups(match_id)
    player_stats = await get_player_stats(match_id)
    events       = await get_match_incidents(match_id)

    details["lineups"]       = lineups
    details["player_stats"]  = player_stats or {}
    details["events"]        = events
    details["played_ids"]    = lineups.get("played_ids", set())
    details["starter_ids"]   = lineups.get("starter_ids", set())

    return details


# ── 7. Auto-discovery for scheduler ───────────────────────────────────────────

async def get_ucl_matches_today_and_yesterday() -> list[dict]:
    """Used by scheduler to auto-detect UCL matches without manual input."""
    from datetime import date, timedelta
    matches = []
    for d in [date.today(), date.today() - timedelta(days=1)]:
        found = await get_ucl_matches_by_date(d.isoformat())
        matches.extend(found)
    return matches
