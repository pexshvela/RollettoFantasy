import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Sheet names inside the DB spreadsheet
SH_USERS     = "users"
SH_SQUADS    = "squads"
SH_TRANSFERS = "transfers"
SH_PENDING   = "pending"

# Column headers
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


_client_cache: gspread.Client | None = None

def _get_client() -> gspread.Client:
    global _client_cache
    if _client_cache is None:
        creds = Credentials.from_service_account_info(config.GOOGLE_CREDENTIALS, scopes=SCOPES)
        _client_cache = gspread.authorize(creds)
    return _client_cache


def _ensure_worksheet(sh, name: str, headers: list) -> gspread.Worksheet:
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)
        logger.info("Created worksheet: %s", name)
    return ws


def _init_db_sync():
    client = _get_client()
    sh = client.open_by_key(config.SHEET_ID_DB)
    _ensure_worksheet(sh, SH_USERS,     USERS_HEADERS)
    _ensure_worksheet(sh, SH_SQUADS,    SQUADS_HEADERS)
    _ensure_worksheet(sh, SH_TRANSFERS, TRANSFERS_HEADERS)
    _ensure_worksheet(sh, SH_PENDING,   PENDING_HEADERS)
    logger.info("DB initialized.")


async def init_db():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _init_db_sync)


# ── User verification ─────────────────────────────────────────────────────────

def _check_username_in_sheet_sync(sheet_id: str, col_name: str, username: str) -> bool:
    client = _get_client()
    sh = client.open_by_key(sheet_id)
    ws = sh.get_worksheet(0)
    data = ws.get_all_records()
    username_lower = username.strip().lower()
    for row in data:
        val = str(row.get(col_name, "")).strip().lower()
        if val == username_lower:
            return True
    return False


async def check_rolletto_username(username: str) -> bool:
    loop = asyncio.get_event_loop()
    found1 = await loop.run_in_executor(
        _executor, _check_username_in_sheet_sync,
        config.SHEET_ID_ROLLETTO_1, config.SHEET_1_USERNAME_COL, username
    )
    if found1:
        return True
    found2 = await loop.run_in_executor(
        _executor, _check_username_in_sheet_sync,
        config.SHEET_ID_ROLLETTO_2, config.SHEET_2_USERNAME_COL, username
    )
    return found2


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_db_ws_sync(name: str) -> tuple[gspread.Client, gspread.Worksheet]:
    client = _get_client()
    sh = client.open_by_key(config.SHEET_ID_DB)
    ws = sh.worksheet(name)
    return client, ws


def _get_user_sync(telegram_id: int) -> dict | None:
    _, ws = _get_db_ws_sync(SH_USERS)
    records = ws.get_all_records()
    for r in records:
        if str(r.get("telegram_id")) == str(telegram_id):
            return r
    return None


async def get_user(telegram_id: int) -> dict | None:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_user_sync, telegram_id)


def _create_user_sync(telegram_id: int, rolletto_username: str, tg_username: str):
    _, ws = _get_db_ws_sync(SH_USERS)
    ws.append_row([
        telegram_id, rolletto_username, tg_username or "",
        "en", "active", datetime.now().isoformat(),
        config.TOTAL_BUDGET, "", "", "no", 0,
    ])


async def create_user(telegram_id: int, rolletto_username: str, tg_username: str = ""):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _create_user_sync, telegram_id, rolletto_username, tg_username)


def _update_user_sync(telegram_id: int, **kwargs):
    _, ws = _get_db_ws_sync(SH_USERS)
    records = ws.get_all_records()
    headers = ws.row_values(1)
    for i, r in enumerate(records, start=2):
        if str(r.get("telegram_id")) == str(telegram_id):
            for key, val in kwargs.items():
                if key in headers:
                    col = headers.index(key) + 1
                    ws.update_cell(i, col, val)
            return


async def update_user(telegram_id: int, **kwargs):
    import functools
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, functools.partial(_update_user_sync, telegram_id, **kwargs))


# ── Squad ─────────────────────────────────────────────────────────────────────

def _get_squad_sync(telegram_id: int) -> dict | None:
    _, ws = _get_db_ws_sync(SH_SQUADS)
    records = ws.get_all_records()
    for r in records:
        if str(r.get("telegram_id")) == str(telegram_id):
            return {k: v for k, v in r.items() if v not in ("", None)}
    return None


async def get_squad(telegram_id: int) -> dict | None:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_squad_sync, telegram_id)


def _save_squad_sync(telegram_id: int, squad: dict):
    _, ws = _get_db_ws_sync(SH_SQUADS)
    records = ws.get_all_records()
    headers = ws.row_values(1)
    for i, r in enumerate(records, start=2):
        if str(r.get("telegram_id")) == str(telegram_id):
            for key, val in squad.items():
                if key in headers:
                    col = headers.index(key) + 1
                    ws.update_cell(i, col, val)
            return
    # New row
    row = [""] * len(headers)
    row[0] = telegram_id
    for key, val in squad.items():
        if key in headers:
            row[headers.index(key)] = val
    ws.append_row(row)


async def save_squad(telegram_id: int, squad: dict):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _save_squad_sync, telegram_id, squad)


# ── Transfers ─────────────────────────────────────────────────────────────────

def _log_transfer_sync(telegram_id: int, matchday: str, player_out: str,
                       player_in: str, free_or_cost: str):
    _, ws = _get_db_ws_sync(SH_TRANSFERS)
    ws.append_row([telegram_id, matchday, player_out, player_in,
                   free_or_cost, datetime.now().isoformat()])


async def log_transfer(telegram_id: int, matchday: str, player_out: str,
                       player_in: str, free_or_cost: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _executor, _log_transfer_sync,
        telegram_id, matchday, player_out, player_in, free_or_cost
    )


# ── Pending ───────────────────────────────────────────────────────────────────

def _add_pending_sync(telegram_id: int, tg_username: str, rolletto_username: str):
    _, ws = _get_db_ws_sync(SH_PENDING)
    records = ws.get_all_records()
    for r in records:
        if str(r.get("telegram_id")) == str(telegram_id):
            return  # already listed
    ws.append_row([telegram_id, tg_username or "", rolletto_username,
                   datetime.now().isoformat()])


async def add_pending(telegram_id: int, tg_username: str, rolletto_username: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _add_pending_sync,
                               telegram_id, tg_username, rolletto_username)


def _get_pending_sync() -> list[dict]:
    _, ws = _get_db_ws_sync(SH_PENDING)
    return ws.get_all_records()


async def get_pending() -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_pending_sync)


# ── Leaderboard ───────────────────────────────────────────────────────────────

def _get_leaderboard_sync() -> list[dict]:
    _, ws = _get_db_ws_sync(SH_USERS)
    records = ws.get_all_records()
    active = [r for r in records if r.get("squad_submitted") == "yes"]
    return sorted(active, key=lambda x: int(x.get("total_points", 0) or 0), reverse=True)[:10]


async def get_leaderboard() -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_leaderboard_sync)


# ── All users (for broadcast) ─────────────────────────────────────────────────

def _get_all_users_sync() -> list[dict]:
    _, ws = _get_db_ws_sync(SH_USERS)
    return ws.get_all_records()


async def get_all_users() -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_all_users_sync)
