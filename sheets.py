import asyncio
import logging
import threading
import functools
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)
_lock = threading.Lock()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SH_USERS     = "users"
SH_SQUADS    = "squads"
SH_TRANSFERS = "transfers"
SH_PENDING   = "pending"

USERS_HEADERS = [
    "telegram_id", "rolletto_username", "tg_username",
    "language", "status", "registration_date",
    "budget_remaining", "formation", "captain",
    "squad_submitted", "total_points",
]
SQUADS_HEADERS = [
    "telegram_id", "formation",
    "gk1",
    "def1", "def2", "def3", "def4", "def5",
    "mf1", "mf2", "mf3", "mf4", "mf5",
    "fw1", "fw2", "fw3",
    "sub1", "sub2", "sub3", "sub4",
]
TRANSFERS_HEADERS = [
    "telegram_id", "matchday", "player_out", "player_in",
    "free_or_cost", "timestamp",
]
PENDING_HEADERS = [
    "telegram_id", "tg_username", "rolletto_username", "timestamp",
]

# ── In-memory cache ───────────────────────────────────────────────────────────
_user_cache: dict = {}
_squad_cache: dict = {}

# ── Connection cache ──────────────────────────────────────────────────────────
_client_obj = None
_db_sheet_obj = None


def _get_client():
    global _client_obj
    with _lock:
        if _client_obj is None:
            creds = Credentials.from_service_account_info(
                config.GOOGLE_CREDENTIALS, scopes=SCOPES
            )
            _client_obj = gspread.authorize(creds)
    return _client_obj


def _get_db():
    global _db_sheet_obj
    with _lock:
        if _db_sheet_obj is None:
            _db_sheet_obj = _get_client().open_by_key(config.SHEET_ID_DB)
    return _db_sheet_obj


def _get_ws(name: str):
    return _get_db().worksheet(name)


# ── DB init ───────────────────────────────────────────────────────────────────

def _ensure_worksheet(sh, name, headers):
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)
        logger.info("Created worksheet: %s", name)
    return ws


def _init_db_sync():
    sh = _get_db()
    _ensure_worksheet(sh, SH_USERS,     USERS_HEADERS)
    _ensure_worksheet(sh, SH_SQUADS,    SQUADS_HEADERS)
    _ensure_worksheet(sh, SH_TRANSFERS, TRANSFERS_HEADERS)
    _ensure_worksheet(sh, SH_PENDING,   PENDING_HEADERS)
    logger.info("DB initialized.")


async def init_db():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_executor, _init_db_sync)


# ── Username verification ──────────────────────────────────────────────────────

def _check_sheet_sync(sheet_id, col_name, username):
    client = _get_client()
    sh = client.open_by_key(sheet_id)
    ws = sh.get_worksheet(0)
    try:
        headers = ws.row_values(1)
        col_idx = headers.index(col_name) + 1
    except (ValueError, Exception):
        return False
    col_vals = ws.col_values(col_idx)
    uname = username.strip().lower()
    return any(str(v).strip().lower() == uname for v in col_vals[1:])


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

def _get_user_sync(telegram_id):
    ws = _get_ws(SH_USERS)
    records = ws.get_all_records()
    for r in records:
        if str(r.get("telegram_id")) == str(telegram_id):
            return dict(r)
    return None


async def get_user(telegram_id: int):
    if telegram_id in _user_cache:
        r = _user_cache[telegram_id]
        return dict(r) if r else None
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_executor, _get_user_sync, telegram_id)
    _user_cache[telegram_id] = result
    return dict(result) if result else None


def _create_user_sync(telegram_id, rolletto_username, tg_username):
    ws = _get_ws(SH_USERS)
    row = [
        telegram_id, rolletto_username, tg_username or "",
        "en", "active", datetime.now().isoformat(),
        config.TOTAL_BUDGET, "", "", "no", 0,
    ]
    ws.append_row(row)
    _user_cache[telegram_id] = dict(zip(USERS_HEADERS, row))


async def create_user(telegram_id: int, rolletto_username: str, tg_username: str = ""):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        _executor, _create_user_sync, telegram_id, rolletto_username, tg_username
    )


def _update_user_sync(telegram_id, **kwargs):
    ws = _get_ws(SH_USERS)
    records = ws.get_all_records()
    headers = ws.row_values(1)
    for i, r in enumerate(records, start=2):
        if str(r.get("telegram_id")) == str(telegram_id):
            updates = []
            for key, val in kwargs.items():
                if key in headers:
                    col = headers.index(key) + 1
                    cell = gspread.utils.rowcol_to_a1(i, col)
                    updates.append({"range": cell, "values": [[val]]})
            if updates:
                ws.batch_update(updates)
            # Keep cache in sync
            cached = _user_cache.get(telegram_id)
            if cached is not None:
                cached.update(kwargs)
            return


async def update_user(telegram_id: int, **kwargs):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        _executor, functools.partial(_update_user_sync, telegram_id, **kwargs)
    )


# ── Squad ──────────────────────────────────────────────────────────────────────

def _get_squad_sync(telegram_id):
    ws = _get_ws(SH_SQUADS)
    records = ws.get_all_records()
    for r in records:
        if str(r.get("telegram_id")) == str(telegram_id):
            return {k: v for k, v in r.items() if v not in ("", None)}
    return None


async def get_squad(telegram_id: int):
    if telegram_id in _squad_cache:
        r = _squad_cache[telegram_id]
        return dict(r) if r else None
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_executor, _get_squad_sync, telegram_id)
    _squad_cache[telegram_id] = result
    return dict(result) if result else None


def _save_squad_sync(telegram_id, squad):
    ws = _get_ws(SH_SQUADS)
    records = ws.get_all_records()
    headers = ws.row_values(1)

    for i, r in enumerate(records, start=2):
        if str(r.get("telegram_id")) == str(telegram_id):
            updates = []
            for key, val in squad.items():
                if key in headers and key != "telegram_id":
                    col = headers.index(key) + 1
                    cell = gspread.utils.rowcol_to_a1(i, col)
                    updates.append({"range": cell, "values": [[val]]})
            if updates:
                ws.batch_update(updates)
            cached = _squad_cache.get(telegram_id) or {}
            cached.update(squad)
            _squad_cache[telegram_id] = cached
            return

    # New row
    row = [""] * len(headers)
    row[0] = telegram_id
    for key, val in squad.items():
        if key in headers:
            row[headers.index(key)] = val
    ws.append_row(row)
    _squad_cache[telegram_id] = dict(squad)


async def save_squad(telegram_id: int, squad: dict):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_executor, _save_squad_sync, telegram_id, squad)


# ── Transfers ──────────────────────────────────────────────────────────────────

def _log_transfer_sync(telegram_id, matchday, player_out, player_in, free_or_cost):
    ws = _get_ws(SH_TRANSFERS)
    ws.append_row([telegram_id, matchday, player_out, player_in,
                   free_or_cost, datetime.now().isoformat()])


async def log_transfer(telegram_id, matchday, player_out, player_in, free_or_cost):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        _executor, _log_transfer_sync,
        telegram_id, matchday, player_out, player_in, free_or_cost
    )


def _get_transfers_used_sync(telegram_id, matchday):
    ws = _get_ws(SH_TRANSFERS)
    records = ws.get_all_records()
    return sum(
        1 for r in records
        if str(r.get("telegram_id")) == str(telegram_id)
        and str(r.get("matchday")) == str(matchday)
    )


async def get_transfers_used(telegram_id: int, matchday: str) -> int:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor, _get_transfers_used_sync, telegram_id, matchday
    )


# ── Pending ───────────────────────────────────────────────────────────────────

def _add_pending_sync(telegram_id, tg_username, rolletto_username):
    ws = _get_ws(SH_PENDING)
    records = ws.get_all_records()
    for r in records:
        if str(r.get("telegram_id")) == str(telegram_id):
            return
    ws.append_row([telegram_id, tg_username or "", rolletto_username,
                   datetime.now().isoformat()])


async def add_pending(telegram_id, tg_username, rolletto_username):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        _executor, _add_pending_sync, telegram_id, tg_username, rolletto_username
    )


async def get_pending():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, lambda: _get_ws(SH_PENDING).get_all_records())


# ── Leaderboard ───────────────────────────────────────────────────────────────

async def get_leaderboard():
    def _sync():
        records = _get_ws(SH_USERS).get_all_records()
        active = [r for r in records if r.get("squad_submitted") == "yes"]
        return sorted(
            active,
            key=lambda x: int(float(x.get("total_points") or 0)),
            reverse=True
        )[:10]
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _sync)


# ── All users ──────────────────────────────────────────────────────────────────

async def get_all_users():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor, lambda: _get_ws(SH_USERS).get_all_records()
    )
