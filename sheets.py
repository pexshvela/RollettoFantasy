"""
sheets.py — Supabase backend + Google Sheets username verification.
"""
import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials
from supabase import create_client, Client

import config

logger = logging.getLogger(__name__)

# ── Simple in-memory cache for frequently read settings ───────────────────────
import time as _time
_cache: dict = {}
_CACHE_TTL = 60  # seconds

# Cache for World Cup eliminated-teams detection (refreshed every 10 min)
_ELIM_CACHE = None
_ELIM_CACHE_TS = 0.0

def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and _time.time() - entry["ts"] < _CACHE_TTL:
        return entry["val"]
    return None

def _cache_set(key: str, val):
    _cache[key] = {"val": val, "ts": _time.time()}

def invalidate_cache(key: str = None):
    """Call when a setting changes so next fetch is fresh."""
    if key:
        _cache.pop(key, None)
    else:
        _cache.clear()

# ── Supabase ──────────────────────────────────────────────────────────────────

_sb: Optional[Client] = None
_sb_lock = threading.Lock()


def _get_sb() -> Client:
    global _sb
    with _sb_lock:
        if _sb is None:
            _sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _sb


async def init_db():
    try:
        _get_sb().table("users").select("telegram_id").limit(1).execute()
        logger.info("Supabase DB connected.")
    except Exception as e:
        logger.error("Supabase connection failed: %s", e)


# ── Google Sheets ─────────────────────────────────────────────────────────────

_gs_client = None
_gs_lock   = threading.Lock()


def _get_gs():
    global _gs_client
    with _gs_lock:
        if _gs_client is None:
            creds_data = json.loads(config.GOOGLE_CREDENTIALS_JSON)
            creds = Credentials.from_service_account_info(
                creds_data,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )
            _gs_client = gspread.authorize(creds)
    return _gs_client


async def verify_username(username: str) -> bool:
    """Check username in Sheet 1 then Sheet 2."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _verify_sync, username)


def _verify_sync(username: str) -> bool:
    try:
        gs = _get_gs()
        username_lower = username.lower().strip()

        # Sheet 1
        try:
            sh1 = gs.open_by_key(config.SHEET_ID_1)
            ws1 = sh1.sheet1
            col_name = config.SHEET_1_USERNAME_COL
            headers  = ws1.row_values(1)
            if col_name in headers:
                col_idx = headers.index(col_name) + 1
                values  = ws1.col_values(col_idx)[1:]
                if any(v.lower().strip() == username_lower for v in values if v):
                    return True
        except Exception as e:
            logger.warning("Sheet 1 error: %s", e)

        # Sheet 2
        try:
            sh2 = gs.open_by_key(config.SHEET_ID_2)
            ws2 = sh2.sheet1
            col_name = config.SHEET_2_USERNAME_COL
            headers  = ws2.row_values(1)
            if col_name in headers:
                col_idx = headers.index(col_name) + 1
                values  = ws2.col_values(col_idx)[1:]
                if any(v.lower().strip() == username_lower for v in values if v):
                    return True
        except Exception as e:
            logger.warning("Sheet 2 error: %s", e)

        return False
    except Exception as e:
        logger.error("verify_username error: %s", e)
        return False


# ── Users ─────────────────────────────────────────────────────────────────────

async def get_user(telegram_id: int) -> Optional[dict]:
    try:
        res = _get_sb().table("users").select("*").eq("telegram_id", telegram_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("get_user error: %s", e)
        return None


async def create_user(telegram_id: int, username: str, language: str, tg_username: str = "") -> dict:
    data = {
        "telegram_id":      telegram_id,
        "rolletto_username": username,
        "tg_username":       tg_username,
        "language":          language,
        "total_points":      0,
        "captain":           "",
        "formation":         "",
    }
    try:
        res = _get_sb().table("users").upsert(data).execute()
        return res.data[0] if res.data else data
    except Exception as e:
        logger.error("create_user error: %s", e)
        return data


async def update_user(telegram_id: int, **kwargs):
    try:
        _get_sb().table("users").update(kwargs).eq("telegram_id", telegram_id).execute()
    except Exception as e:
        logger.error("update_user error: %s", e)


async def get_user_by_rolletto_username(username: str) -> dict | None:
    """Check if a rolletto username is already registered to any telegram_id."""
    try:
        res = _get_sb().table("users").select("*").ilike("rolletto_username", username.strip()).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


async def get_all_users() -> list[dict]:
    try:
        res = _get_sb().table("users").select("*").execute()
        return res.data or []
    except Exception as e:
        logger.error("get_all_users error: %s", e)
        return []


# ── Squads ────────────────────────────────────────────────────────────────────

async def get_squad(telegram_id: int) -> Optional[dict]:
    try:
        res = _get_sb().table("squads").select("*").eq("telegram_id", telegram_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("get_squad error: %s", e)
        return None


async def save_squad(telegram_id: int, squad_data: dict):
    try:
        data = {"telegram_id": telegram_id, **squad_data}
        _get_sb().table("squads").upsert(data).execute()
    except Exception as e:
        logger.error("save_squad error: %s", e)


async def get_all_squads() -> list[dict]:
    try:
        res = _get_sb().table("squads").select("*").execute()
        return res.data or []
    except Exception as e:
        logger.error("get_all_squads error: %s", e)
        return []


# ── Confirmations ─────────────────────────────────────────────────────────────

async def confirm_squad(telegram_id: int, gameweek_id: int, squad_snapshot: dict,
                         intentional: bool = False):
    """Save/update a user's confirmation.

    `intentional=True` → user explicitly tapped "Confirm Squad" button.
       This is the only path that sets confirmed_at for first-time users.
    `intentional=False` → auto-save from transfer/sub-swap.
       Updates squad_snapshot but does NOT set confirmed_at on first-time users
       (otherwise a transfer would be retroactively treated as "joining now").

    confirmed_at is set ONLY on the first intentional confirmation and never
    overwritten on subsequent updates. This preserves the original commitment
    timestamp so the scheduler's carry-forward filter
    (confirmed_at <= match kickoff) works correctly."""
    try:
        # Check if a confirmation row already exists for this user
        existing = _get_sb().table("confirmations").select("confirmed_at").eq(
            "telegram_id", telegram_id
        ).execute()
        row_exists = bool(existing.data)
        has_confirmed_at = row_exists and existing.data[0].get("confirmed_at")

        row = {
            "telegram_id":     telegram_id,
            "gameweek_id":     gameweek_id,
            "squad_snapshot":  json.dumps(squad_snapshot),
        }
        if has_confirmed_at:
            # Preserve original confirmed_at — never overwritten
            row["confirmed_at"] = existing.data[0]["confirmed_at"]
        elif intentional:
            # First intentional confirmation — stamp it now
            row["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        else:
            # Auto-save (transfer/sub swap) for a user who never intentionally
            # confirmed yet. Save the squad but leave confirmed_at NULL — they
            # haven't actually committed their participation yet.
            row["confirmed_at"] = None
        _get_sb().table("confirmations").upsert(row).execute()
    except Exception as e:
        logger.error("confirm_squad error: %s", e)


async def get_latest_confirmation(telegram_id: int) -> Optional[dict]:
    """Get the most recent confirmation for a user across all gameweeks."""
    try:
        res = _get_sb().table("confirmations").select("*").eq(
            "telegram_id", telegram_id
        ).order("gameweek_id", desc=True).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("get_latest_confirmation error: %s", e)
        return None


async def get_confirmation(telegram_id: int, gameweek_id: int) -> Optional[dict]:
    try:
        res = _get_sb().table("confirmations").select("*").eq(
            "telegram_id", telegram_id
        ).eq("gameweek_id", gameweek_id).execute()
        if res.data:
            row = res.data[0]
            if isinstance(row.get("squad_snapshot"), str):
                row["squad_snapshot"] = json.loads(row["squad_snapshot"])
            return row
        return None
    except Exception as e:
        logger.error("get_confirmation error: %s", e)
        return None


async def get_all_confirmations(gameweek_id: int) -> list[dict]:
    try:
        res = _get_sb().table("confirmations").select("*").eq("gameweek_id", gameweek_id).execute()
        rows = res.data or []
        for r in rows:
            if isinstance(r.get("squad_snapshot"), str):
                try:
                    r["squad_snapshot"] = json.loads(r["squad_snapshot"])
                except Exception:
                    r["squad_snapshot"] = {}
        return rows
    except Exception as e:
        logger.error("get_all_confirmations error: %s", e)
        return []


# ── Transfers ─────────────────────────────────────────────────────────────────

async def log_transfer(telegram_id: int, player_out: str, player_in: str,
                       gameweek_id: int, cost_pts: int):
    try:
        _get_sb().table("transfers").insert({
            "telegram_id":  telegram_id,
            "player_out":   player_out,
            "player_in":    player_in,
            "matchday":     gameweek_id,
            "free_or_cost": cost_pts,
        }).execute()
    except Exception as e:
        logger.error("log_transfer error: %s", e)


async def count_transfers_this_gw(telegram_id: int, gameweek_id: int) -> int:
    try:
        res = _get_sb().table("transfers").select("id").eq(
            "telegram_id", telegram_id
        ).eq("matchday", gameweek_id).execute()
        return len(res.data or [])
    except Exception as e:
        logger.error("count_transfers error: %s", e)
        return 0


async def count_transfers_since(telegram_id: int, since_iso: str) -> int:
    """Count transfers a user made at/after a timestamp (transfer-window open).
    Used so 'free transfers per window' resets cleanly even when gameweeks are
    created per calendar date."""
    if not since_iso:
        return 0
    try:
        res = _get_sb().table("transfers").select("id").eq(
            "telegram_id", telegram_id
        ).gte("timestamp", since_iso).execute()
        return len(res.data or [])
    except Exception as e:
        logger.error("count_transfers_since error: %s", e)
        return 0


async def count_transfers_used(telegram_id: int, gameweek_id: int) -> int:
    """How many transfers count against the user's free allowance right now.

    WC: per-matchday gameweek is the natural reset boundary → count per gameweek.
    PL/UCL: gameweeks are per calendar date, so counting per gameweek would reset
    the allowance mid-round. Instead count transfers since the current transfer
    window opened (admin-controlled). Falls back to per-gameweek if no window."""
    try:
        tournament = await get_tournament()
        if tournament == "wc":
            return await count_transfers_this_gw(telegram_id, gameweek_id)
        ts = await get_transfer_settings()
        open_iso = ts.get("open")
        if open_iso:
            return await count_transfers_since(telegram_id, open_iso)
        return await count_transfers_this_gw(telegram_id, gameweek_id)
    except Exception:
        return await count_transfers_this_gw(telegram_id, gameweek_id)


async def get_transfer_costs_by_user(telegram_ids: list) -> dict[int, int]:
    """Return {telegram_id: total point cost of all their transfers}.
    Used by the scoring recompute so extra-transfer hits persist in total_points."""
    if not telegram_ids:
        return {}
    try:
        res = _get_sb().table("transfers").select(
            "telegram_id,free_or_cost"
        ).in_("telegram_id", [str(u) for u in telegram_ids]).execute()
        costs: dict[int, int] = {}
        for r in (res.data or []):
            uid = int(r["telegram_id"])
            costs[uid] = costs.get(uid, 0) + int(r.get("free_or_cost") or 0)
        return costs
    except Exception as e:
        logger.error("get_transfer_costs_by_user error: %s", e)
        return {}


# ── Gameweeks ─────────────────────────────────────────────────────────────────

async def get_active_gameweek() -> Optional[dict]:
    cached = _cache_get("active_gameweek")
    if cached is not None:
        return cached
    try:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        res = _get_sb().table("gameweeks").select("*").gte(
            "start_date", today
        ).order("start_date").limit(1).execute()
        if res.data:
            result = res.data[0]
            _cache_set("active_gameweek", result)
            return result
        res2 = _get_sb().table("gameweeks").select("*").order(
            "start_date", desc=True
        ).limit(1).execute()
        result = res2.data[0] if res2.data else None
        _cache_set("active_gameweek", result)
        return result
    except Exception as e:
        logger.error("get_active_gameweek error: %s", e)
        return None


async def get_active_round() -> dict | None:
    """Return active round info: {number, name, round_str, deadline}.
    Picks the round with the most UPCOMING matches (not a single postponed
    makeup match that would otherwise hijack the display)."""
    try:
        import football_api as _fapi
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        tournament = await get_tournament()

        relevant_round = None
        try:
            sb = _get_sb()
            now_ts = _dt.now(_tz.utc).timestamp()
            # Look back up to 7 days so we don't lose a round mid-matchday.
            seven_days_ago = now_ts - (7 * 24 * 3600)
            res = sb.table("match_cache").select(
                "match_id,round,kickoff_timestamp,status,points_awarded"
            ).order("kickoff_timestamp").execute()
            rows = res.data or []

            # First preference: rounds that have at least one match that is
            # upcoming OR recently kicked off (within 7 days) AND not yet
            # fully awarded. This keeps us on the current round even when
            # matches spread across several days (WC group stage).
            active_by_round: dict[str, list[int]] = {}
            future_by_round: dict[str, list[int]] = {}
            for m in rows:
                ts = int(m.get("kickoff_timestamp") or 0)
                rnd = (m.get("round") or "").strip()
                if not rnd:
                    continue
                awarded = m.get("points_awarded", False)
                if ts >= now_ts:
                    # Purely future match
                    future_by_round.setdefault(rnd, []).append(ts)
                elif ts >= seven_days_ago:
                    # Recent match (within 7 days)
                    active_by_round.setdefault(rnd, []).append(ts)

            # Pick the earliest round that still has future or recent matches
            # that haven't been fully processed, preferring rounds with future
            # matches still to play.
            candidate_rounds = set(active_by_round) | set(future_by_round)
            if candidate_rounds:
                def round_sort_key(rnd):
                    import football_api as _fapi2
                    md = _fapi2.wc_matchday(rnd)
                    # For WC: prefer by matchday number; non-WC: by earliest kickoff
                    if md:
                        return (md, 0)
                    kickoffs = (active_by_round.get(rnd, []) + future_by_round.get(rnd, []))
                    return (999, min(kickoffs) if kickoffs else 0)
                relevant_round = sorted(candidate_rounds, key=round_sort_key)[0]
            else:
                # No upcoming or recent matches — use most recent finished round
                for m in reversed(rows):
                    rnd = (m.get("round") or "").strip()
                    if rnd:
                        relevant_round = rnd
                        break
        except Exception as inner:
            logger.warning("get_active_round match_cache lookup failed: %s", inner)

        # Last resort: ask API (note: API can be laggy)
        if not relevant_round:
            relevant_round = await _fapi.get_current_round(tournament)

        if not relevant_round:
            gw = await get_active_gameweek()
            if gw:
                return {"number": gw.get("id"), "name": gw.get("name", ""), "deadline": gw.get("deadline")}
            return None

        round_str = relevant_round
        num = _fapi.parse_round_number(round_str)
        display = _fapi.round_display_name(round_str)
        deadline_key = num if num is not None else round_str.lower().replace(" ", "_").replace("-", "_")
        deadline = await get_round_deadline(deadline_key)
        return {
            "number": num,
            "name": display,
            "round_str": round_str,
            "deadline_key": deadline_key,
            "deadline": deadline,
        }
    except Exception as e:
        logger.error("get_active_round error: %s", e)
        return None


async def get_round_deadline(round_key) -> Optional[str]:
    """Get deadline for a round. round_key can be int or string slug."""
    return await get_setting(f"round_deadline_{round_key}")


async def set_round_deadline(round_key, deadline_iso: str):
    """Set deadline for a round. round_key can be int or string slug."""
    await set_setting(f"round_deadline_{round_key}", deadline_iso)
    _cache_set("active_gameweek", None)





async def get_gameweek(gw_id: int) -> Optional[dict]:
    try:
        res = _get_sb().table("gameweeks").select("*").eq("id", gw_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("get_gameweek error: %s", e)
        return None


async def get_all_gameweeks() -> list[dict]:
    try:
        res = _get_sb().table("gameweeks").select("*").order("start_date").execute()
        return res.data or []
    except Exception as e:
        logger.error("get_all_gameweeks error: %s", e)
        return []


async def create_gameweek(name: str, tournament_id: int, start_date: str,
                           end_date: str, deadline: str) -> Optional[dict]:
    try:
        res = _get_sb().table("gameweeks").insert({
            "name":          name,
            "tournament_id": tournament_id,
            "start_date":    start_date,
            "end_date":      end_date,
            "deadline":      deadline,
            "status":        "upcoming",
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("create_gameweek error: %s", e)
        return None


async def update_gameweek(gw_id: int, **kwargs):
    try:
        _get_sb().table("gameweeks").update(kwargs).eq("id", gw_id).execute()
    except Exception as e:
        logger.error("update_gameweek error: %s", e)


# ── Match cache ───────────────────────────────────────────────────────────────

async def get_cached_match(match_id: str) -> Optional[dict]:
    try:
        res = _get_sb().table("match_cache").select("*").eq("match_id", str(match_id)).execute()
        if res.data:
            row = res.data[0]
            for f in ("events", "player_stats"):
                if isinstance(row.get(f), str):
                    try: row[f] = json.loads(row[f])
                    except: row[f] = {} if f == "player_stats" else []
            return row
        return None
    except Exception as e:
        logger.error("get_cached_match error: %s", e)
        return None


async def save_match_cache(match: dict):
    try:
        _get_sb().table("match_cache").upsert({
            "match_id":          str(match["id"]),
            "home_team":         match.get("home_team", ""),
            "away_team":         match.get("away_team", ""),
            "home_team_id":      str(match.get("home_team_id", "") or ""),
            "away_team_id":      str(match.get("away_team_id", "") or ""),
            "home_score":        match.get("home_score", 0),
            "away_score":        match.get("away_score", 0),
            "status":            match.get("status", "scheduled"),
            "match_date":        match.get("date", ""),
            "match_time":        match.get("time", ""),
            "kickoff_timestamp": match.get("kickoff_timestamp", 0),
            "tournament":        match.get("tournament", ""),
            "round":             match.get("round", ""),
            "events":            json.dumps(match.get("events", [])),
            "player_stats":      json.dumps(match.get("player_stats", {})),
            "points_awarded":    match.get("points_awarded", False),
            "last_checked":      match.get("last_checked", 0),
        }).execute()
    except Exception as e:
        logger.error("save_match_cache error: %s", e)


async def mark_match_points_awarded(match_id: str):
    try:
        _get_sb().table("match_cache").update(
            {"points_awarded": True}
        ).eq("match_id", str(match_id)).execute()
    except Exception as e:
        logger.error("mark_match_points_awarded error: %s", e)


async def update_match_last_checked(match_id: str):
    try:
        _get_sb().table("match_cache").update(
            {"last_checked": int(time.time())}
        ).eq("match_id", str(match_id)).execute()
    except Exception as e:
        logger.error("update_match_last_checked error: %s", e)


async def get_unprocessed_matches() -> list[dict]:
    """Matches that are due but not yet points_awarded."""
    try:
        res = _get_sb().table("match_cache").select(
            "match_id,home_team,away_team,home_score,away_score,"
            "status,match_date,kickoff_timestamp,last_checked,points_awarded"
        ).eq("points_awarded", False).order("kickoff_timestamp").execute()
        return res.data or []
    except Exception as e:
        logger.error("get_unprocessed_matches error: %s", e)
        return []


async def get_upcoming_matches(days: int = 7) -> list[dict]:
    from datetime import date, timedelta
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    today  = date.today().isoformat()
    try:
        res = _get_sb().table("match_cache").select("*")             .gte("match_date", today)             .lte("match_date", cutoff)             .order("match_date").execute()
        rows = res.data or []
        for r in rows:
            for f in ("events", "player_stats"):
                if isinstance(r.get(f), str):
                    try:
                        import json
                        r[f] = json.loads(r[f])
                    except Exception:
                        r[f] = []
        return rows
    except Exception as e:
        logger.error("get_upcoming_matches error: %s", e)
        return []


async def update_match_cache(match_id: str, fields: dict):
    """Update specific fields in an existing match_cache row."""
    import json
    try:
        data = {}
        for k, v in fields.items():
            data[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
        _get_sb().table("match_cache").update(data).eq("match_id", str(match_id)).execute()
    except Exception as e:
        logger.error("update_match_cache error: %s", e)


async def get_recent_matches(days: int = 3, tournament: str = None) -> list[dict]:
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    try:
        q = _get_sb().table("match_cache").select("*").gte("match_date", cutoff).order("match_date", desc=True)
        res = q.execute()
        rows = res.data or []
        # Filter by tournament if specified
        if tournament:
            TOURNAMENT_NAMES = {
                "pl":  ["premier league"],
                "ucl": ["uefa champions league", "champions league"],
                "wc":  ["world cup", "fifa world cup"],
            }
            keywords = TOURNAMENT_NAMES.get(tournament.lower(), [tournament.lower()])
            rows = [r for r in rows
                    if any(k in str(r.get("tournament", "")).lower() for k in keywords)]
        for r in rows:
            for f in ("events", "player_stats"):
                if isinstance(r.get(f), str):
                    try: r[f] = json.loads(r[f])
                    except: r[f] = {} if f == "player_stats" else []
        return rows
    except Exception as e:
        logger.error("get_recent_matches error: %s", e)
        return []


# ── Player match points ───────────────────────────────────────────────────────

async def save_player_points(telegram_id: int, player_id: str,
                              match_id: str, gameweek_id: int,
                              points: int, breakdown: dict):
    try:
        _get_sb().table("player_match_points").upsert({
            "telegram_id":  telegram_id,
            "player_id":    player_id,
            "match_id":     match_id,
            "gameweek_id":  gameweek_id,
            "points":       points,
            "breakdown":    json.dumps(breakdown),
        }, on_conflict="telegram_id,player_id,match_id").execute()
    except Exception as e:
        logger.error("save_player_points error: %s", e)


async def get_player_points_history(telegram_id: int,
                                    player_id: str) -> list[dict]:
    try:
        res = _get_sb().table("player_match_points").select("*").eq(
            "telegram_id", telegram_id
        ).eq("player_id", player_id).order("created_at", desc=True).execute()
        rows = res.data or []
        for r in rows:
            if isinstance(r.get("breakdown"), str):
                try: r["breakdown"] = json.loads(r["breakdown"])
                except: r["breakdown"] = {}
        return rows
    except Exception as e:
        logger.error("get_player_points_history error: %s", e)
        return []


async def get_squad_points_summary(telegram_id: int) -> dict[str, int]:
    try:
        res = _get_sb().table("player_match_points").select(
            "player_id,points"
        ).eq("telegram_id", telegram_id).execute()
        summary: dict[str, int] = {}
        for r in (res.data or []):
            pid = r["player_id"]
            summary[pid] = summary.get(pid, 0) + (r["points"] or 0)
        return summary
    except Exception as e:
        logger.error("get_squad_points_summary error: %s", e)
        return {}


async def get_gameweek_points(telegram_id: int, gameweek_id: int) -> int:
    try:
        res = _get_sb().table("player_match_points").select("points").eq(
            "telegram_id", telegram_id
        ).eq("gameweek_id", gameweek_id).execute()
        return sum(r["points"] or 0 for r in (res.data or []))
    except Exception as e:
        logger.error("get_gameweek_points error: %s", e)
        return 0


# ── Leaderboard ───────────────────────────────────────────────────────────────

async def get_overall_rank(telegram_id: int) -> tuple[int, int]:
    """Return (rank, total_points) for a user in the overall standings,
    using standard competition ranking (ties share a rank: 5,5,7).
    Rank is 1-based. Returns (0, 0) if the user has no record."""
    try:
        sb = _get_sb()
        me = sb.table("users").select("total_points").eq(
            "telegram_id", telegram_id
        ).limit(1).execute()
        if not me.data:
            return (0, 0)
        my_pts = int(me.data[0].get("total_points") or 0)
        # Count users strictly above me; rank = that count + 1
        above = sb.table("users").select(
            "telegram_id", count="exact"
        ).gt("total_points", my_pts).execute()
        rank = (above.count or 0) + 1
        return (rank, my_pts)
    except Exception as e:
        logger.error("get_overall_rank error: %s", e)
        return (0, 0)


async def get_round_rank(telegram_id: int, round_str: str) -> tuple[int, int]:
    """Return (rank, points) for a user within a specific round's standings,
    standard competition ranking. Returns (0, 0) if no data for the round."""
    try:
        if not round_str:
            return (0, 0)
        full = await get_round_leaderboard(round_str, limit=100000)
        my_pts = None
        for r in full:
            if r.get("telegram_id") == telegram_id:
                my_pts = r.get("total_points", 0)
                break
        if my_pts is None:
            return (0, 0)
        above = sum(1 for r in full if r.get("total_points", 0) > my_pts)
        return (above + 1, my_pts)
    except Exception as e:
        logger.error("get_round_rank error: %s", e)
        return (0, 0)


async def get_overall_leaderboard(limit: int = 20) -> list[dict]:
    try:
        res = _get_sb().table("users").select(
            "telegram_id,rolletto_username,tg_username,username,total_points"
        ).order("total_points", desc=True).limit(limit).execute()
        # Normalize username field for display
        rows = []
        for r in (res.data or []):
            r["username"] = r.get("rolletto_username") or r.get("tg_username") or r.get("username") or "?"
            rows.append(r)
        return rows
    except Exception as e:
        logger.error("get_overall_leaderboard error: %s", e)
        return []


async def get_round_leaderboard(round_str: str, limit: int = 20) -> list[dict]:
    """Leaderboard for a specific round, computed from the matches that actually
    belong to that round (match_cache.round == round_str). This avoids the fragile
    round→gameweek_id name-substring mapping, which breaks when gameweeks are
    created per calendar date rather than per round."""
    try:
        sb = _get_sb()
        if not round_str:
            return []
        mc = sb.table("match_cache").select("match_id").eq("round", round_str).execute()
        match_ids = [str(r["match_id"]) for r in (mc.data or []) if r.get("match_id") is not None]
        if not match_ids:
            return []

        pts_res = sb.table("player_match_points").select(
            "telegram_id,points"
        ).in_("match_id", match_ids).execute()
        totals: dict[int, int] = {}
        for r in (pts_res.data or []):
            uid = int(r["telegram_id"])
            totals[uid] = totals.get(uid, 0) + int(r.get("points") or 0)

        users_res = sb.table("users").select(
            "telegram_id,rolletto_username,tg_username,username"
        ).execute()
        result = []
        for u in (users_res.data or []):
            uid = int(u["telegram_id"])
            result.append({
                "telegram_id": uid,
                "username": u.get("rolletto_username") or u.get("tg_username") or u.get("username") or "?",
                "total_points": totals.get(uid, 0),
            })
        result.sort(key=lambda x: -x["total_points"])
        return result[:limit]
    except Exception as e:
        logger.error("get_round_leaderboard error: %s", e)
        return []


async def get_gameweek_leaderboard(gameweek_id: int, limit: int = 20) -> list[dict]:
    try:
        # Get all points for this gameweek
        res = _get_sb().table("player_match_points").select(
            "telegram_id,points"
        ).eq("gameweek_id", gameweek_id).execute()

        # Aggregate per user
        totals: dict[int, int] = {}
        for r in (res.data or []):
            uid = r["telegram_id"]
            totals[uid] = totals.get(uid, 0) + (r["points"] or 0)

        # Fetch all users in one query to avoid N+1
        all_users_res = _get_sb().table("users").select(
            "telegram_id,rolletto_username,tg_username,username,total_points"
        ).execute()
        # Normalize username for display
        for u in (all_users_res.data or []):
            u["username"] = u.get("rolletto_username") or u.get("tg_username") or u.get("username") or "?"
        uid_to_user = {int(u["telegram_id"]): u for u in (all_users_res.data or [])}

        # Include ALL confirmed users — even those with 0 pts this GW
        # Users not in totals get 0 for this GW
        result = []
        for u in uid_to_user.values():
            uid = int(u["telegram_id"])
            pts = totals.get(uid, 0)
            result.append({
                "telegram_id": uid,
                "username": u.get("rolletto_username") or u.get("tg_username") or u.get("username") or "?",
                "total_points": pts
            })

        # Sort by GW points descending, limit
        result.sort(key=lambda x: -x["total_points"])
        return result[:limit]
    except Exception as e:
        logger.error("get_gameweek_leaderboard error: %s", e)
        return []


# ── Bot settings ──────────────────────────────────────────────────────────────

async def get_setting(key: str, default=None):
    cache_key = f"setting:{key}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        res = _get_sb().table("bot_settings").select("value").eq("key", key).execute()
        if res.data:
            try:
                val = json.loads(res.data[0]["value"])
            except Exception:
                val = res.data[0]["value"]
            _cache_set(cache_key, val)
            return val
    except Exception:
        pass
    return default


async def set_setting(key: str, value):
    invalidate_cache(f"setting:{key}")  # Invalidate cache on write
    invalidate_cache("active_gameweek")
    try:
        v = json.dumps(value) if not isinstance(value, str) else value
        _get_sb().table("bot_settings").upsert({"key": key, "value": v}).execute()
    except Exception as e:
        logger.error("set_setting error: %s", e)


async def get_tournament() -> str:
    return await get_setting("active_tournament", config.DEFAULT_TOURNAMENT)


async def get_wc_matchday() -> int | None:
    """Current World Cup matchday (1-7) based on the active round.
    Returns None if not in WC or round can't be determined."""
    try:
        import football_api as _fapi
        rnd = await get_active_round()
        if not rnd:
            return None
        round_str = rnd.get("round_str") or rnd.get("name") or ""
        return _fapi.wc_matchday(round_str)
    except Exception:
        return None


async def get_max_per_nation() -> int:
    """Max players allowed per club/nation for the active tournament.
    PL/UCL: fixed MAX_PLAYERS_PER_CLUB. WC: scales by matchday
    (group=3, R16=4, QF=5, SF=6, Final=8)."""
    try:
        tournament = await get_tournament()
        if tournament == "wc":
            md = await get_wc_matchday()
            if md and md in config.WC_MAX_PER_NATION:
                return config.WC_MAX_PER_NATION[md]
            return 3  # default to group-stage cap
        return config.MAX_PLAYERS_PER_CLUB
    except Exception:
        return config.MAX_PLAYERS_PER_CLUB


async def get_transfer_rules() -> dict:
    """Tournament-aware transfer rules.
    Returns {free: int, extra_cost: int} where free=0 means unlimited.
    PL/UCL: from settings + config.EXTRA_TRANSFER_COST.
    WC: per-matchday allowance map + WC_EXTRA_TRANSFER_COST (-3)."""
    try:
        tournament = await get_tournament()
        if tournament == "wc":
            md = await get_wc_matchday()
            allowance = config.WC_TRANSFER_ALLOWANCE.get(md, 1) if md else 1
            # -1 means unlimited → represent as 0 (the codebase treats 0 as unlimited)
            free = 0 if allowance == -1 else allowance
            return {"free": free, "extra_cost": config.WC_EXTRA_TRANSFER_COST}
        # PL/UCL: use existing setting
        ts = await get_transfer_settings()
        free = ts.get("free", config.FREE_TRANSFERS_DEFAULT)
        return {"free": free, "extra_cost": config.EXTRA_TRANSFER_COST}
    except Exception:
        return {"free": config.FREE_TRANSFERS_DEFAULT, "extra_cost": config.EXTRA_TRANSFER_COST}


async def get_eliminated_teams() -> set:
    """Return set of team names eliminated from the World Cup.
    A team is 'eliminated' once it has no remaining upcoming/future fixtures.
    Only meaningful for WC; returns empty set for other tournaments.

    Detection: look at match_cache for the active tournament. A team that has
    played at least one match but has NO match with kickoff in the future
    (status not finished) is considered eliminated. Cached for 10 min to avoid
    hammering the DB on every picker render."""
    try:
        tournament = await get_tournament()
        if tournament != "wc":
            return set()

        # Simple in-process cache (10 min)
        import time as _time
        global _ELIM_CACHE, _ELIM_CACHE_TS
        now = _time.time()
        if _ELIM_CACHE is not None and (now - _ELIM_CACHE_TS) < 600:
            return _ELIM_CACHE

        sb = _get_sb()
        res = sb.table("match_cache").select(
            "home_team,away_team,kickoff_timestamp,status,round"
        ).execute()
        rows = res.data or []
        if not rows:
            _ELIM_CACHE, _ELIM_CACHE_TS = set(), now
            return set()

        FINISHED = {"final", "ft", "match finished", "aet", "pen", "finished"}
        now_ts = int(now)
        teams_played = set()
        teams_with_future = set()
        for m in rows:
            home = (m.get("home_team") or "").strip()
            away = (m.get("away_team") or "").strip()
            ts = int(m.get("kickoff_timestamp") or 0)
            status = (m.get("status") or "").lower()
            is_finished = status in FINISHED
            for tm in (home, away):
                if not tm:
                    continue
                if is_finished or ts <= now_ts:
                    teams_played.add(tm)
                # A team has a "future" presence if there's a match not yet finished
                if (not is_finished) and ts > now_ts:
                    teams_with_future.add(tm)

        # Eliminated = played at least one match, but has no future fixtures.
        # Guard: if NO team has future fixtures (e.g. between rounds before the
        # next round is scheduled), don't mark everyone eliminated.
        if not teams_with_future:
            _ELIM_CACHE, _ELIM_CACHE_TS = set(), now
            return set()

        eliminated = teams_played - teams_with_future
        _ELIM_CACHE, _ELIM_CACHE_TS = eliminated, now
        return eliminated
    except Exception as e:
        logger.warning("get_eliminated_teams error: %s", e)
        return set()


async def get_transfer_settings() -> dict:
    return {
        "open":   await get_setting("transfer_window_open", None),
        "close":  await get_setting("transfer_window_close", None),
        "free":   await get_setting("free_transfers", config.FREE_TRANSFERS_DEFAULT),
    }


async def is_transfer_window_open() -> bool:
    ts = await get_transfer_settings()
    if not ts["open"] or not ts["close"]:
        return False
    now = datetime.now(timezone.utc).isoformat()
    return ts["open"] <= now <= ts["close"]


async def get_confirmation_deadline() -> Optional[str]:
    """Get the effective deadline: round-specific first, then global fallback."""
    try:
        rnd = await get_active_round()
        if rnd:
            # Use deadline_key which works for both numbered (35) and named (semi_finals) rounds
            key = rnd.get("deadline_key") or rnd.get("number")
            if key is not None:
                round_dl = await get_round_deadline(key)
                if round_dl:
                    return round_dl
    except Exception:
        pass
    return await get_setting("confirmation_deadline", None)


async def is_before_deadline() -> bool:
    deadline = await get_confirmation_deadline()
    if not deadline:
        return True  # no deadline set = always open
    now = datetime.now(timezone.utc).isoformat()
    return now < deadline


async def get_kickoff_windows() -> list[dict]:
    """Group all upcoming/live matches into kickoff windows.
    Matches within 30 minutes of each other share a window.
    Returns list of {kickoff_ts, end_ts_estimate, deadline, match_ids, finished, all_done}.
    Sorted by kickoff_ts ascending."""
    try:
        sb = _get_sb()
        res = sb.table("match_cache").select(
            "match_id,home_team,away_team,kickoff_timestamp,status,points_awarded"
        ).order("kickoff_timestamp").execute()
        FINAL_STATUSES = {"final", "ft", "match finished", "aet", "pen", "finished"}
        # Filter to matches with a real kickoff timestamp
        rows = [m for m in (res.data or []) if m.get("kickoff_timestamp")]
        # Group by kickoff within 30 min
        windows: list[dict] = []
        for m in rows:
            ts = m["kickoff_timestamp"]
            placed = False
            for w in windows:
                if abs(ts - w["kickoff_ts"]) <= 1800:  # 30 min
                    w["matches"].append(m)
                    # Window kickoff is the EARLIEST in the group
                    if ts < w["kickoff_ts"]:
                        w["kickoff_ts"] = ts
                    placed = True
                    break
            if not placed:
                windows.append({"kickoff_ts": ts, "matches": [m]})
        # Compute deadline (1h before earliest kickoff) and all_done flag
        for w in windows:
            w["deadline_ts"] = w["kickoff_ts"] - 3600
            # Window's all_done = every match in it is finished or points awarded
            all_done = True
            for m in w["matches"]:
                status = str(m.get("status") or "").lower()
                if status not in FINAL_STATUSES and not m.get("points_awarded"):
                    all_done = False
                    break
            w["all_done"]   = all_done
            w["match_ids"]  = [m["match_id"] for m in w["matches"]]
        return windows
    except Exception as e:
        logger.error("get_kickoff_windows error: %s", e)
        return []


async def is_swap_window_open() -> bool:
    """Sub swaps are open if NO kickoff window is currently in its locked period.
    Locked period = from (kickoff - 1h) until all matches in window are finished."""
    try:
        windows = await get_kickoff_windows()
        now_ts = datetime.now(timezone.utc).timestamp()
        for w in windows:
            # Window is locked from (kickoff - 1h) until all matches finished
            lock_start = w["kickoff_ts"] - 3600
            if now_ts < lock_start:
                continue  # window not started yet
            if w["all_done"]:
                continue  # window finished
            return False  # we are inside a locked window
        return True  # no active locked window
    except Exception as e:
        logger.error("is_swap_window_open error: %s", e)
        # Fail CLOSED: if we can't verify the window is open, don't allow swaps.
        # Better to briefly block a legit swap than to permit one during a
        # locked kickoff window and corrupt scoring fairness.
        return False


async def get_next_window_status() -> dict | None:
    """Return info about the most relevant window for display:
    {state: 'open'|'locked'|'before_first', deadline_ts, kickoff_ts, all_done}.
    Used to show users the next deadline."""
    try:
        windows = await get_kickoff_windows()
        if not windows:
            return None
        now_ts = datetime.now(timezone.utc).timestamp()
        for w in windows:
            lock_start = w["kickoff_ts"] - 3600
            if w["all_done"]:
                continue
            if now_ts < lock_start:
                # Next deadline is this window's lock_start
                return {
                    "state": "open",
                    "deadline_ts": lock_start,
                    "kickoff_ts": w["kickoff_ts"],
                    "all_done": False,
                }
            else:
                # Currently locked
                return {
                    "state": "locked",
                    "deadline_ts": lock_start,
                    "kickoff_ts": w["kickoff_ts"],
                    "all_done": False,
                }
        return None
    except Exception as e:
        logger.error("get_next_window_status error: %s", e)
        return None


# ── Reset ─────────────────────────────────────────────────────────────────────

async def reset_user(telegram_id: int):
    """Reset a single user — squad, points, transfers, confirmation."""
    try:
        sb = _get_sb()
        sb.table("squads").delete().eq("telegram_id", telegram_id).execute()
        sb.table("confirmations").delete().eq("telegram_id", telegram_id).execute()
        sb.table("transfers").delete().eq("telegram_id", telegram_id).execute()
        sb.table("player_match_points").delete().eq("telegram_id", telegram_id).execute()
        sb.table("users").update({
            "total_points": 0,
            "captain": "", "formation": "",
        }).eq("telegram_id", telegram_id).execute()
    except Exception as e:
        logger.error("reset_user error: %s", e)


async def reset_for_tournament_change():
    """Reset all squads, confirmations, transfers and points for a tournament switch.
    Keeps match_cache and gameweeks intact."""
    try:
        sb = _get_sb()
        sb.table("squads").delete().neq("telegram_id", 0).execute()
        sb.table("confirmations").delete().neq("telegram_id", 0).execute()
        sb.table("transfers").delete().neq("telegram_id", 0).execute()
        sb.table("player_match_points").delete().neq("telegram_id", 0).execute()
        sb.table("users").update({
            "total_points": 0,
            "captain": "",
            "formation": "",
        }).neq("telegram_id", 0).execute()
    except Exception as e:
        logger.error("reset_for_tournament_change error: %s", e)


async def reset_all():
    """Full campaign reset."""
    try:
        sb = _get_sb()
        sb.table("squads").delete().neq("telegram_id", 0).execute()
        sb.table("confirmations").delete().neq("telegram_id", 0).execute()
        sb.table("transfers").delete().neq("telegram_id", 0).execute()
        sb.table("player_match_points").delete().neq("telegram_id", 0).execute()
        sb.table("match_cache").delete().neq("match_id", "").execute()
        sb.table("gameweeks").delete().neq("id", 0).execute()
        sb.table("users").update({
            "total_points": 0,
            "captain": "", "formation": "",
        }).neq("telegram_id", 0).execute()
    except Exception as e:
        logger.error("reset_all error: %s", e)
