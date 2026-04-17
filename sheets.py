"""
sheets.py — Supabase backend for the Rolletto Fantasy bot DB.
Google Sheets is still used ONLY for username verification (sheets 1 & 2).
"""
import asyncio
import logging
import functools
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import gspread
from google.oauth2.service_account import Credentials
from supabase import create_client, Client

import config

logger = logging.getLogger(__name__)

# ── Supabase client ───────────────────────────────────────────────────────────
_sb: Client | None = None
_sb_lock = threading.Lock()


def _get_sb() -> Client:
    global _sb
    with _sb_lock:
        if _sb is None:
            _sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _sb


# ── In-memory cache (so repeated reads are instant) ───────────────────────────
_user_cache: dict = {}
_squad_cache: dict = {}

# ── Thread executor for sync gspread calls ────────────────────────────────────
_executor = ThreadPoolExecutor(max_workers=2)

# ── Google Sheets (verification only) ────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
_gs_client = None
_gs_lock = threading.Lock()


def _get_gs():
    global _gs_client
    with _gs_lock:
        if _gs_client is None:
            creds = Credentials.from_service_account_info(
                config.GOOGLE_CREDENTIALS, scopes=SCOPES
            )
            _gs_client = gspread.authorize(creds)
    return _gs_client


# ── DB init ───────────────────────────────────────────────────────────────────

async def init_db():
    """Test Supabase connection — tables are already created via SQL editor."""
    try:
        _get_sb().table("users").select("telegram_id").limit(1).execute()
        logger.info("Supabase DB connected.")
    except Exception as e:
        logger.error("Supabase connection failed: %s", e)
        raise


# ── Username verification (Google Sheets) ────────────────────────────────────

def _check_sheet_sync(sheet_id: str, col_name: str, username: str) -> bool:
    try:
        gs = _get_gs()
        sh = gs.open_by_key(sheet_id)
        ws = sh.get_worksheet(0)
        headers = ws.row_values(1)
        col_idx = headers.index(col_name) + 1
        col_vals = ws.col_values(col_idx)
        uname = username.strip().lower()
        return any(str(v).strip().lower() == uname for v in col_vals[1:])
    except Exception as e:
        logger.error("Sheet check error: %s", e)
        return False


async def check_rolletto_username(username: str) -> bool:
    loop = asyncio.get_running_loop()
    found = await loop.run_in_executor(
        _executor, _check_sheet_sync,
        config.SHEET_ID_ROLLETTO_1, config.SHEET_1_USERNAME_COL, username
    )
    if found:
        return True
    return await loop.run_in_executor(
        _executor, _check_sheet_sync,
        config.SHEET_ID_ROLLETTO_2, config.SHEET_2_USERNAME_COL, username
    )


# ── Users ─────────────────────────────────────────────────────────────────────

async def get_user(telegram_id: int) -> dict | None:
    if telegram_id in _user_cache:
        r = _user_cache[telegram_id]
        return dict(r) if r else None
    try:
        res = _get_sb().table("users").select("*").eq("telegram_id", telegram_id).execute()
        result = res.data[0] if res.data else None
        _user_cache[telegram_id] = result
        return dict(result) if result else None
    except Exception as e:
        logger.error("get_user error: %s", e)
        return None


async def create_user(telegram_id: int, rolletto_username: str, tg_username: str = ""):
    row = {
        "telegram_id": telegram_id,
        "rolletto_username": rolletto_username,
        "tg_username": tg_username or "",
        "language": "en",
        "status": "active",
        "registration_date": datetime.now().isoformat(),
        "budget_remaining": config.TOTAL_BUDGET,
        "formation": "",
        "captain": "",
        "squad_submitted": "no",
        "total_points": 0,
    }
    try:
        _get_sb().table("users").upsert(row).execute()
        _user_cache[telegram_id] = row
    except Exception as e:
        logger.error("create_user error: %s", e)


async def update_user(telegram_id: int, **kwargs):
    try:
        _get_sb().table("users").update(kwargs).eq("telegram_id", telegram_id).execute()
        cached = _user_cache.get(telegram_id)
        if cached is not None:
            cached.update(kwargs)
    except Exception as e:
        logger.error("update_user error: %s", e)


# ── Squad ──────────────────────────────────────────────────────────────────────

async def get_squad(telegram_id: int) -> dict | None:
    if telegram_id in _squad_cache:
        r = _squad_cache[telegram_id]
        return dict(r) if r else None
    try:
        res = _get_sb().table("squads").select("*").eq("telegram_id", telegram_id).execute()
        result = res.data[0] if res.data else None
        if result:
            # Remove None values for cleaner handling downstream
            result = {k: v for k, v in result.items() if v is not None and v != ""}
        _squad_cache[telegram_id] = result
        return dict(result) if result else None
    except Exception as e:
        logger.error("get_squad error: %s", e)
        return None


async def save_squad(telegram_id: int, squad: dict):
    try:
        # Explicitly send None for empty slots so Supabase CLEARS the column.
        # Without this, upsert ignores missing keys and keeps old values.
        all_slots = [
            "formation", "gk1",
            "def1", "def2", "def3", "def4", "def5",
            "mf1",  "mf2",  "mf3",  "mf4",  "mf5",
            "fw1",  "fw2",  "fw3",
            "sub1", "sub2", "sub3", "sub4",
        ]
        data = {"telegram_id": telegram_id}
        for key in all_slots:
            val = squad.get(key, None)
            data[key] = None if val == "" else val
        _get_sb().table("squads").upsert(data).execute()
        # Replace cache entirely — never use .update() which keeps removed keys
        _squad_cache[telegram_id] = {
            k: v for k, v in squad.items() if v not in ("", None)
        }
    except Exception as e:
        logger.error("save_squad error: %s", e)


# ── Transfers ──────────────────────────────────────────────────────────────────

async def log_transfer(telegram_id: int, matchday: str, player_out: str,
                       player_in: str, free_or_cost: str):
    try:
        _get_sb().table("transfers").insert({
            "telegram_id": telegram_id,
            "matchday": matchday,
            "player_out": player_out,
            "player_in": player_in,
            "free_or_cost": free_or_cost,
            "timestamp": datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        logger.error("log_transfer error: %s", e)


async def get_transfers_used(telegram_id: int, matchday: str) -> int:
    try:
        res = _get_sb().table("transfers")\
            .select("id")\
            .eq("telegram_id", telegram_id)\
            .eq("matchday", matchday)\
            .execute()
        return len(res.data)
    except Exception as e:
        logger.error("get_transfers_used error: %s", e)
        return 0


# ── Pending ───────────────────────────────────────────────────────────────────

async def add_pending(telegram_id: int, tg_username: str, rolletto_username: str):
    try:
        _get_sb().table("pending").upsert({
            "telegram_id": telegram_id,
            "tg_username": tg_username or "",
            "rolletto_username": rolletto_username,
            "timestamp": datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        logger.error("add_pending error: %s", e)


async def get_pending() -> list:
    try:
        res = _get_sb().table("pending").select("*").execute()
        return res.data or []
    except Exception as e:
        logger.error("get_pending error: %s", e)
        return []


# ── Leaderboard ───────────────────────────────────────────────────────────────

async def get_leaderboard() -> list:
    try:
        res = _get_sb().table("users")\
            .select("rolletto_username,total_points")\
            .eq("squad_submitted", "yes")\
            .order("total_points", desc=True)\
            .limit(10)\
            .execute()
        return res.data or []
    except Exception as e:
        logger.error("get_leaderboard error: %s", e)
        return []


# ── All users (broadcast) ─────────────────────────────────────────────────────

async def get_all_users() -> list:
    try:
        res = _get_sb().table("users").select("telegram_id,language").execute()
        return res.data or []
    except Exception as e:
        logger.error("get_all_users error: %s", e)
        return []


# ── Reset helpers ─────────────────────────────────────────────────────────────

async def reset_users(telegram_ids: list[int]):
    """Reset squad, budget, points for specific user(s)."""
    sb = _get_sb()
    for tid in telegram_ids:
        try:
            sb.table("users").update({
                "budget_remaining": __import__("config").TOTAL_BUDGET,
                "formation": "",
                "captain": "",
                "squad_submitted": "no",
                "total_points": 0,
            }).eq("telegram_id", tid).execute()
            sb.table("squads").delete().eq("telegram_id", tid).execute()
            _user_cache.pop(tid, None)
            _squad_cache.pop(tid, None)
        except Exception as e:
            logger.error("reset_users error for %s: %s", tid, e)


async def reset_campaign():
    """
    Full campaign reset — wipes all squads & transfers,
    resets every user's budget/points/formation/captain/squad_submitted.
    Users remain registered.
    """
    import config as _config
    sb = _get_sb()
    # Delete all squads and transfers
    sb.table("squads").delete().neq("telegram_id", 0).execute()
    sb.table("transfers").delete().neq("id", 0).execute()
    # Reset every user
    sb.table("users").update({
        "budget_remaining": _config.TOTAL_BUDGET,
        "formation": "",
        "captain": "",
        "squad_submitted": "no",
        "total_points": 0,
    }).neq("telegram_id", 0).execute()
    # Clear all in-memory caches
    _user_cache.clear()
    _squad_cache.clear()


# ── Match cache ───────────────────────────────────────────────────────────────

async def get_cached_match(match_id: str) -> dict | None:
    try:
        res = _get_sb().table("match_cache").select("*").eq("match_id", match_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("get_cached_match error: %s", e)
        return None


async def save_match_cache(match: dict):
    """
    match dict: id, home_team, away_team, home_score, away_score,
                status, date, events (list), player_stats (dict)
    """
    import json
    try:
        _get_sb().table("match_cache").upsert({
            "match_id":       match["id"],
            "home_team":      match.get("home_team", ""),
            "away_team":      match.get("away_team", ""),
            "home_score":     match.get("home_score", 0),
            "away_score":     match.get("away_score", 0),
            "status":         match.get("status", "scheduled"),
            "match_date":     match.get("date", ""),
            "tournament":     match.get("tournament", ""),
            "tournament_url": match.get("tournament_url", ""),
            "events":         json.dumps(match.get("events", [])),
            "player_stats":   json.dumps(match.get("player_stats", {})),
            "points_awarded": match.get("points_awarded", False),
        }).execute()
    except Exception as e:
        logger.error("save_match_cache error: %s", e)


async def mark_match_points_awarded(match_id: str):
    try:
        _get_sb().table("match_cache").update(
            {"points_awarded": True}
        ).eq("match_id", match_id).execute()
    except Exception as e:
        logger.error("mark_match_points_awarded error: %s", e)


async def get_recent_matches(days: int = 2) -> list[dict]:
    """Get all cached matches from the last N days, newest first."""
    from datetime import date, timedelta
    import json
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    try:
        res = _get_sb().table("match_cache").select("*").gte(
            "match_date", cutoff
        ).order("match_date", desc=True).execute()
        rows = res.data or []
        # Parse JSON fields
        for r in rows:
            if isinstance(r.get("events"), str):
                try:
                    r["events"] = json.loads(r["events"])
                except Exception:
                    r["events"] = []
            if isinstance(r.get("player_stats"), str):
                try:
                    r["player_stats"] = json.loads(r["player_stats"])
                except Exception:
                    r["player_stats"] = {}
        return rows
    except Exception as e:
        logger.error("get_recent_matches error: %s", e)
        return []


# ── Player match points ───────────────────────────────────────────────────────

async def save_player_match_points(telegram_id: int, player_id: str,
                                   match_id: str, points: int, breakdown: dict):
    import json
    try:
        _get_sb().table("player_match_points").upsert({
            "telegram_id": telegram_id,
            "player_id":   player_id,
            "match_id":    match_id,
            "points":      points,
            "breakdown":   json.dumps(breakdown),
        }).execute()
    except Exception as e:
        logger.error("save_player_match_points error: %s", e)


async def get_player_points_history(telegram_id: int, player_id: str) -> list[dict]:
    """All point entries for a player in a user's squad, newest first."""
    import json
    try:
        res = _get_sb().table("player_match_points").select(
            "*, match_cache(home_team, away_team, home_score, away_score, match_date)"
        ).eq("telegram_id", telegram_id).eq("player_id", player_id).order(
            "created_at", desc=True
        ).execute()
        rows = res.data or []
        for r in rows:
            if isinstance(r.get("breakdown"), str):
                try:
                    r["breakdown"] = json.loads(r["breakdown"])
                except Exception:
                    r["breakdown"] = {}
        return rows
    except Exception as e:
        logger.error("get_player_points_history error: %s", e)
        return []


async def get_squad_points_summary(telegram_id: int) -> dict[str, int]:
    """Total points per player_id for this user."""
    try:
        res = _get_sb().table("player_match_points").select(
            "player_id, points"
        ).eq("telegram_id", telegram_id).execute()
        summary: dict[str, int] = {}
        for r in (res.data or []):
            pid = r["player_id"]
            summary[pid] = summary.get(pid, 0) + (r["points"] or 0)
        return summary
    except Exception as e:
        logger.error("get_squad_points_summary error: %s", e)
        return {}


# ── Match watchlist ───────────────────────────────────────────────────────────

async def add_to_watchlist(match_id: str):
    try:
        _get_sb().table("match_watchlist").upsert({
            "match_id": match_id,
            "processed": False,
        }).execute()
    except Exception as e:
        logger.error("add_to_watchlist error: %s", e)


async def get_watchlist() -> list[dict]:
    """Get all unprocessed matches from watchlist."""
    try:
        res = _get_sb().table("match_watchlist").select("*").eq("processed", False).execute()
        return res.data or []
    except Exception as e:
        logger.error("get_watchlist error: %s", e)
        return []


async def mark_watchlist_processed(match_id: str):
    try:
        _get_sb().table("match_watchlist").update(
            {"processed": True}
        ).eq("match_id", match_id).execute()
    except Exception as e:
        logger.error("mark_watchlist_processed error: %s", e)


async def remove_from_watchlist(match_id: str):
    try:
        _get_sb().table("match_watchlist").delete().eq("match_id", match_id).execute()
    except Exception as e:
        logger.error("remove_from_watchlist error: %s", e)


# ── Bot settings (key-value store) ────────────────────────────────────────────

async def get_setting(key: str, default=None):
    """Get a bot setting from Supabase. Falls back to default."""
    try:
        res = _get_sb().table("bot_settings").select("value").eq("key", key).execute()
        if res.data:
            import json
            try:
                return json.loads(res.data[0]["value"])
            except Exception:
                return res.data[0]["value"]
    except Exception:
        pass
    return default


async def set_setting(key: str, value):
    """Save a bot setting to Supabase."""
    import json
    try:
        _get_sb().table("bot_settings").upsert({
            "key": key,
            "value": json.dumps(value) if not isinstance(value, str) else value
        }).execute()
    except Exception as e:
        logger.error("set_setting error: %s", e)


async def get_tournament_keywords() -> list:
    """Get current tournament filter — returns list of ints (SofaScore IDs) or strings."""
    import config
    setting = await get_setting("tournament_ids", config.DEFAULT_TOURNAMENT_IDS)
    if setting is not None:
        return setting
    # fallback to keyword list for backward compat
    return await get_setting("tournament_keywords", config.DEFAULT_TOURNAMENT_KEYWORDS)


async def get_tournament_ids() -> list[int]:
    """Get current tournament IDs for SportAPI7 filtering."""
    import config
    ids = await get_setting("tournament_ids", config.DEFAULT_TOURNAMENT_IDS)
    if ids and isinstance(ids[0], int):
        return ids
    return config.DEFAULT_TOURNAMENT_IDS
