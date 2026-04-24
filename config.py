"""
config.py — All environment variables and constants.
"""
import os

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
ADMIN_ID    = int(os.getenv("ADMIN_ID", "5194165418"))

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Google Sheets
SHEET_ID_1          = os.getenv("SHEET_ID_ROLLETTO_1", "")
SHEET_ID_2          = os.getenv("SHEET_ID_ROLLETTO_2", "")
SHEET_1_USERNAME_COL = os.getenv("SHEET_1_USERNAME_COL", "USERNAME")
SHEET_2_USERNAME_COL = os.getenv("SHEET_2_USERNAME_COL", "rolletto_username")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "{}")

# api-football (api-sports.io direct)
API_FOOTBALL_KEY  = os.getenv("API_FOOTBALL_KEY", "e23260ce6329642ba416e6e185140894")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"

# Fantasy settings
TOTAL_BUDGET           = int(os.getenv("TOTAL_BUDGET", "100000000"))  # 100M
FREE_TRANSFERS_DEFAULT = int(os.getenv("FREE_TRANSFERS_DEFAULT", "2"))
EXTRA_TRANSFER_COST    = int(os.getenv("EXTRA_TRANSFER_COST", "4"))  # -4 pts

# Rolletto signup URL
ROLLETTO_SIGNUP_URL = os.getenv("ROLLETTO_SIGNUP_URL", "https://rolletto.com")

# Tournament modes
TOURNAMENT_UCL = "ucl"
TOURNAMENT_PL  = "pl"

# api-football league IDs
LEAGUE_IDS = {
    "ucl": {"league": 2,  "season": 2024},  # UCL 2024/25
    "pl":  {"league": 39, "season": 2025},  # PL 2025/26
}

# Default active tournament
DEFAULT_TOURNAMENT = os.getenv("DEFAULT_TOURNAMENT", "ucl")

# Scheduler
SCHEDULER_POLL_MINUTES  = 5
MATCH_DUE_MINUTES       = 100   # check API 100 min after kickoff
MATCH_RETRY_MINUTES     = 15    # retry every 15 min if not finished
