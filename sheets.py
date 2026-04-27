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


async def create_user(telegram_id: int, username: str, language: str) -> dict:
    data = {
        "telegram_id":   telegram_id,
        "username":      username,
        "language":      language,
        "total_points":  0,
        "confirmed":     False,
        "captain":       "",
        "formation":     "",
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

async def confirm_squad(telegram_id: int, gameweek_id: int, squad_snapshot: dict):
    try:
        _get_sb().table("confirmations").upsert({
            "telegram_id":     telegram_id,
            "gameweek_id":     gameweek_id,
            "confirmed_at":    datetime.now(timezone.utc).isoformat(),
            "squad_snapshot":  json.dumps(squad_snapshot),
        }).execute()
        await update_user(telegram_id, confirmed=True)
    except Exception as e:
        logger.error("confirm_squad error: %s", e)


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
            "gameweek_id":  gameweek_id,
            "cost_pts":     cost_pts,
        }).execute()
    except Exception as e:
        logger.error("log_transfer error: %s", e)


async def count_transfers_this_gw(telegram_id: int, gameweek_id: int) -> int:
    try:
        res = _get_sb().table("transfers").select("id").eq(
            "telegram_id", telegram_id
        ).eq("gameweek_id", gameweek_id).execute()
        return len(res.data or [])
    except Exception as e:
        logger.error("count_transfers error: %s", e)
        return 0


# ── Gameweeks ─────────────────────────────────────────────────────────────────

async def get_active_gameweek() -> Optional[dict]:
    try:
        res = _get_sb().table("gameweeks").select("*").in_(
            "status", ["upcoming", "active"]
        ).order("start_date").limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error("get_active_gameweek error: %s", e)
        return None


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
        res = _get_sb().table("match_cache").select("*").eq("match_id", match_id).execute()
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
            "match_id":          match["id"],
            "home_team":         match.get("home_team", ""),
            "away_team":         match.get("away_team", ""),
            "home_score":        match.get("home_score", 0),
            "away_score":        match.get("away_score", 0),
            "status":            match.get("status", "scheduled"),
            "match_date":        match.get("date", ""),
            "match_time":        match.get("time", ""),
            "kickoff_timestamp": match.get("kickoff_timestamp", 0),
            "tournament":        match.get("tournament", ""),
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
        ).eq("match_id", match_id).execute()
    except Exception as e:
        logger.error("mark_match_points_awarded error: %s", e)


async def update_match_last_checked(match_id: str):
    try:
        _get_sb().table("match_cache").update(
            {"last_checked": int(time.time())}
        ).eq("match_id", match_id).execute()
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


async def update_match_cache(match_id: str, fields: dict):
    """Update specific fields in an existing match_cache row."""
    import json
    try:
        data = {}
        for k, v in fields.items():
            data[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
        _get_sb().table("match_cache").update(data).eq("match_id", match_id).execute()
    except Exception as e:
        logger.error("update_match_cache error: %s", e)


async def get_recent_matches(days: int = 3, tournament: str = None) -> list[dict]:
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    try:
        q = _get_sb().table("match_cache").select("*").gte("match_date", cutoff).order("match_date", desc=True)
        res = q.execute()
        rows = res.data or []
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
        }).execute()
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

async def get_overall_leaderboard(limit: int = 20) -> list[dict]:
    try:
        res = _get_sb().table("users").select(
            "telegram_id,username,total_points"
        ).order("total_points", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.error("get_overall_leaderboard error: %s", e)
        return []


async def get_gameweek_leaderboard(gameweek_id: int, limit: int = 20) -> list[dict]:
    try:
        res = _get_sb().table("player_match_points").select(
            "telegram_id,points"
        ).eq("gameweek_id", gameweek_id).execute()
        # Aggregate per user
        totals: dict[int, int] = {}
        for r in (res.data or []):
            uid = r["telegram_id"]
            totals[uid] = totals.get(uid, 0) + (r["points"] or 0)
        # Get usernames
        result = []
        for uid, pts in sorted(totals.items(), key=lambda x: -x[1])[:limit]:
            user = await get_user(uid)
            if user:
                result.append({"telegram_id": uid,
                                "username": user.get("username", "?"),
                                "total_points": pts})
        return result
    except Exception as e:
        logger.error("get_gameweek_leaderboard error: %s", e)
        return []


# ── Bot settings ──────────────────────────────────────────────────────────────

async def get_setting(key: str, default=None):
    try:
        res = _get_sb().table("bot_settings").select("value").eq("key", key).execute()
        if res.data:
            try:
                return json.loads(res.data[0]["value"])
            except Exception:
                return res.data[0]["value"]
    except Exception:
        pass
    return default


async def set_setting(key: str, value):
    try:
        v = json.dumps(value) if not isinstance(value, str) else value
        _get_sb().table("bot_settings").upsert({"key": key, "value": v}).execute()
    except Exception as e:
        logger.error("set_setting error: %s", e)


async def get_tournament() -> str:
    return await get_setting("active_tournament", config.DEFAULT_TOURNAMENT)


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
    return await get_setting("confirmation_deadline", None)


async def is_before_deadline() -> bool:
    deadline = await get_confirmation_deadline()
    if not deadline:
        return True  # no deadline set = always open
    now = datetime.now(timezone.utc).isoformat()
    return now < deadline


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
            "total_points": 0, "confirmed": False,
            "captain": "", "formation": "",
        }).eq("telegram_id", telegram_id).execute()
    except Exception as e:
        logger.error("reset_user error: %s", e)


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
            "total_points": 0, "confirmed": False,
            "captain": "", "formation": "",
        }).neq("telegram_id", 0).execute()
    except Exception as e:
        logger.error("reset_all error: %s", e)
