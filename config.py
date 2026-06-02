"""
config.py — All environment variables and constants.
"""
import os

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
# No hardcoded default — must be supplied via env. 0 means "no admin configured".
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0") or "0")

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
# No hardcoded default — supply via env. (Any previously committed key should be rotated.)
API_FOOTBALL_KEY  = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"

# Fantasy settings
TOTAL_BUDGET           = int(os.getenv("TOTAL_BUDGET", "100000000"))  # 100M
FREE_TRANSFERS_DEFAULT = int(os.getenv("FREE_TRANSFERS_DEFAULT", "1"))  # 1 per GW (official)
MAX_BANKED_TRANSFERS   = int(os.getenv("MAX_BANKED_TRANSFERS", "5"))    # bank up to 5
EXTRA_TRANSFER_COST    = int(os.getenv("EXTRA_TRANSFER_COST", "4"))  # -4 pts
MAX_PLAYERS_PER_CLUB   = int(os.getenv("MAX_PLAYERS_PER_CLUB", "3"))  # max per club

# Rolletto signup URL
ROLLETTO_SIGNUP_URL = os.getenv("ROLLETTO_SIGNUP_URL", "https://rolletto.com")

# Tournament modes
TOURNAMENT_UCL = "ucl"
TOURNAMENT_PL  = "pl"
TOURNAMENT_WC  = "wc"

# api-football league IDs
LEAGUE_IDS = {
    "ucl": {"league": 2,  "season": 2024},  # UCL 2024/25
    "pl":  {"league": 39, "season": 2025},  # PL 2025/26
    "wc":  {"league": 1,  "season": 2026},  # FIFA World Cup 2026
}

# ── World Cup-specific rules ───────────────────────────────────────────────
# Per-matchday free-transfer allowance. -1 means unlimited.
# MD1 unlimited, MD2=2, MD3=2, MD4 unlimited (knockouts start), MD5=4, MD6=5, MD7=6
WC_TRANSFER_ALLOWANCE = {1: -1, 2: 2, 3: 2, 4: -1, 5: 4, 6: 5, 7: 6}
# Extra transfer cost for World Cup (official: -3, not -4)
WC_EXTRA_TRANSFER_COST = 3
# Dynamic max players per nation by matchday (group=3, then scales each knockout round)
WC_MAX_PER_NATION = {1: 3, 2: 3, 3: 3, 4: 4, 5: 5, 6: 6, 7: 8}

# Default active tournament
DEFAULT_TOURNAMENT = os.getenv("DEFAULT_TOURNAMENT", "pl")

# Scheduler
SCHEDULER_POLL_MINUTES  = 5
MATCH_DUE_MINUTES       = 100   # check API 100 min after kickoff
MATCH_RETRY_MINUTES     = 15    # retry every 15 min if not finished
