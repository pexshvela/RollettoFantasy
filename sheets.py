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
        data = {"telegram_id": telegram_id, **squad}
        _get_sb().table("squads").upsert(data).execute()
        cached = _squad_cache.get(telegram_id) or {}
        cached.update(squad)
        _squad_cache[telegram_id] = cached
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
