import os
import json
from dotenv import load_dotenv

load_dotenv()

# ── Core ─────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5194165418"))

# ── Football API ──────────────────────────────────────────────────────────────
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
FOOTBALL_API_BASE = "https://api.football-data.org/v4"

# ── Google Sheets ─────────────────────────────────────────────────────────────
SHEET_ID_ROLLETTO_1 = os.getenv("SHEET_ID_ROLLETTO_1")   # USERNAME col
SHEET_ID_ROLLETTO_2 = os.getenv("SHEET_ID_ROLLETTO_2")   # rolletto_username col
SHEET_ID_DB         = os.getenv("SHEET_ID_DB")            # bot database
SHEET_1_USERNAME_COL = os.getenv("SHEET_1_USERNAME_COL", "USERNAME")
SHEET_2_USERNAME_COL = os.getenv("SHEET_2_USERNAME_COL", "rolletto_username")

# ── Game ──────────────────────────────────────────────────────────────────────
ROLLETTO_SIGNUP_URL        = os.getenv("ROLLETTO_SIGNUP_URL", "https://rolletto.space/RollettoFantasy")
TOTAL_BUDGET               = int(os.getenv("TOTAL_BUDGET", "100000000"))
FREE_TRANSFERS_PER_MATCHDAY = int(os.getenv("FREE_TRANSFERS_PER_MATCHDAY", "2"))
EXTRA_TRANSFER_COST_PTS    = int(os.getenv("EXTRA_TRANSFER_COST_PTS", "4"))
SQUAD_LOCK_HOURS_BEFORE    = int(os.getenv("SQUAD_LOCK_HOURS_BEFORE", "1"))

# ── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ── Google credentials ────────────────────────────────────────────────────────
_raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "{}")
try:
    GOOGLE_CREDENTIALS = json.loads(_raw)
except json.JSONDecodeError:
    GOOGLE_CREDENTIALS = {}

# ── Formations supported ─────────────────────────────────────────────────────
FORMATIONS = {
    "4-3-3": {"DEF": 4, "MF": 3, "FW": 3},
    "4-4-2": {"DEF": 4, "MF": 4, "FW": 2},
    "3-4-3": {"DEF": 3, "MF": 4, "FW": 3},
    "3-5-2": {"DEF": 3, "MF": 5, "FW": 2},
    "5-3-2": {"DEF": 5, "MF": 3, "FW": 2},
    "4-5-1": {"DEF": 4, "MF": 5, "FW": 1},
}

SUPPORTED_LANGUAGES = ["en", "it", "fr", "es"]
