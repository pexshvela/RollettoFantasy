"""
players.py — Player roster for Rolletto Fantasy UCL Bot.

espn_id: ESPN numeric player ID used by the RapidAPI UCL endpoint.
         Call /athlete/overview?playerId=<espn_id> to verify.
espn_name: Display name as returned by the API (for fuzzy matching).

⚠️  Verify ESPN IDs using the API before launch:
    GET /athlete/bio?playerId=<id> — should return the correct player name.
"""

PLAYERS = {
    "GK": [
        {"id": "gk1", "name": "Alisson",    "team": "Liverpool",   "nation": "🇧🇷", "price": 7000000,  "espn_id": 193232, "espn_name": "Alisson"},
        {"id": "gk2", "name": "Ter Stegen", "team": "Barcelona",   "nation": "🇩🇪", "price": 6000000,  "espn_id": 174374, "espn_name": "M. ter Stegen"},
        {"id": "gk3", "name": "Ederson",    "team": "Man City",    "nation": "🇧🇷", "price": 6500000,  "espn_id": 235017, "espn_name": "Ederson"},
        {"id": "gk4", "name": "Courtois",   "team": "Real Madrid", "nation": "🇧🇪", "price": 7500000,  "espn_id": 68093,  "espn_name": "T. Courtois"},
        {"id": "gk5", "name": "Donnarumma", "team": "PSG",         "nation": "🇮🇹", "price": 6000000,  "espn_id": 229591, "espn_name": "G. Donnarumma"},
        {"id": "gk6", "name": "Sommer",     "team": "Inter",       "nation": "🇨🇭", "price": 5000000,  "espn_id": 107901, "espn_name": "Y. Sommer"},
        {"id": "gk7", "name": "Neuer",      "team": "Bayern",      "nation": "🇩🇪", "price": 5500000,  "espn_id": 48007,  "espn_name": "M. Neuer"},
        {"id": "gk8", "name": "Raya",       "team": "Arsenal",     "nation": "🇪🇸", "price": 5500000,  "espn_id": 237591, "espn_name": "D. Raya"},
    ],
    "DEF": [
        {"id": "def1",  "name": "Van Dijk",         "team": "Liverpool",   "nation": "🇳🇱", "price": 8000000,  "espn_id": 220601, "espn_name": "V. van Dijk"},
        {"id": "def2",  "name": "Alexander-Arnold", "team": "Real Madrid", "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 8500000,  "espn_id": 272345, "espn_name": "T. Alexander-Arnold"},
        {"id": "def3",  "name": "Rüdiger",          "team": "Real Madrid", "nation": "🇩🇪", "price": 7000000,  "espn_id": 179685, "espn_name": "A. Rüdiger"},
        {"id": "def4",  "name": "Robertson",        "team": "Liverpool",   "nation": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "price": 6000000,  "espn_id": 234093, "espn_name": "A. Robertson"},
        {"id": "def5",  "name": "Militão",          "team": "Real Madrid", "nation": "🇧🇷", "price": 7500000,  "espn_id": 262975, "espn_name": "E. Militão"},
        {"id": "def6",  "name": "Hakimi",           "team": "PSG",         "nation": "🇲🇦", "price": 8000000,  "espn_id": 291086, "espn_name": "A. Hakimi"},
        {"id": "def7",  "name": "T. Hernandez",     "team": "Bayern",      "nation": "🇫🇷", "price": 7000000,  "espn_id": 262959, "espn_name": "T. Hernández"},
        {"id": "def8",  "name": "Pavard",           "team": "Inter",       "nation": "🇫🇷", "price": 6000000,  "espn_id": 215541, "espn_name": "B. Pavard"},
        {"id": "def9",  "name": "Upamecano",        "team": "Bayern",      "nation": "🇫🇷", "price": 6000000,  "espn_id": 346151, "espn_name": "D. Upamecano"},
        {"id": "def10", "name": "Saliba",           "team": "Arsenal",     "nation": "🇫🇷", "price": 7500000,  "espn_id": 364936, "espn_name": "W. Saliba"},
        {"id": "def11", "name": "White",            "team": "Arsenal",     "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 6000000,  "espn_id": 282621, "espn_name": "B. White"},
        {"id": "def12", "name": "Koundé",           "team": "Barcelona",   "nation": "🇫🇷", "price": 7000000,  "espn_id": 291734, "espn_name": "J. Koundé"},
        {"id": "def13", "name": "Balde",            "team": "Barcelona",   "nation": "🇪🇸", "price": 5500000,  "espn_id": 383547, "espn_name": "A. Balde"},
        {"id": "def14", "name": "Gvardiol",         "team": "Man City",    "nation": "🇭🇷", "price": 7000000,  "espn_id": 356965, "espn_name": "J. Gvardiol"},
        {"id": "def15", "name": "Stones",           "team": "Man City",    "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 6000000,  "espn_id": 194984, "espn_name": "J. Stones"},
        {"id": "def16", "name": "Bastoni",          "team": "Inter",       "nation": "🇮🇹", "price": 7000000,  "espn_id": 307800, "espn_name": "A. Bastoni"},
    ],
    "MF": [
        {"id": "mf1",  "name": "Bellingham", "team": "Real Madrid", "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 12000000, "espn_id": 224604, "espn_name": "J. Bellingham"},
        {"id": "mf2",  "name": "De Bruyne",  "team": "Man City",    "nation": "🇧🇪", "price": 9000000,  "espn_id": 136207, "espn_name": "K. De Bruyne"},
        {"id": "mf3",  "name": "Pedri",      "team": "Barcelona",   "nation": "🇪🇸", "price": 9000000,  "espn_id": 340282, "espn_name": "Pedri"},
        {"id": "mf4",  "name": "Rodri",      "team": "Man City",    "nation": "🇪🇸", "price": 8000000,  "espn_id": 255971, "espn_name": "Rodri"},
        {"id": "mf5",  "name": "Vitinha",    "team": "PSG",         "nation": "🇵🇹", "price": 7000000,  "espn_id": 355553, "espn_name": "Vitinha"},
        {"id": "mf6",  "name": "Rice",       "team": "Arsenal",     "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 9000000,  "espn_id": 273316, "espn_name": "D. Rice"},
        {"id": "mf7",  "name": "Modric",     "team": "Real Madrid", "nation": "🇭🇷", "price": 6000000,  "espn_id": 46945,  "espn_name": "L. Modrić"},
        {"id": "mf8",  "name": "Gündogan",   "team": "Barcelona",   "nation": "🇩🇪", "price": 6500000,  "espn_id": 137274, "espn_name": "I. Gündogan"},
        {"id": "mf9",  "name": "Calhanoglu", "team": "Inter",       "nation": "🇹🇷", "price": 7000000,  "espn_id": 176534, "espn_name": "H. Çalhanoğlu"},
        {"id": "mf10", "name": "Musiala",    "team": "Bayern",      "nation": "🇩🇪", "price": 10000000, "espn_id": 399007, "espn_name": "J. Musiala"},
        {"id": "mf11", "name": "Ødegaard",   "team": "Arsenal",     "nation": "🇳🇴", "price": 9000000,  "espn_id": 309452, "espn_name": "M. Ødegaard"},
        {"id": "mf12", "name": "Barella",    "team": "Inter",       "nation": "🇮🇹", "price": 7500000,  "espn_id": 292736, "espn_name": "N. Barella"},
        {"id": "mf13", "name": "Kimmich",    "team": "Bayern",      "nation": "🇩🇪", "price": 7500000,  "espn_id": 215549, "espn_name": "J. Kimmich"},
        {"id": "mf14", "name": "Saka",       "team": "Arsenal",     "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 10000000, "espn_id": 291721, "espn_name": "B. Saka"},
        {"id": "mf15", "name": "Yamal",      "team": "Barcelona",   "nation": "🇪🇸", "price": 11000000, "espn_id": 1008089,"espn_name": "L. Yamal"},
    ],
    "FW": [
        {"id": "fw1",  "name": "Mbappé",      "team": "Real Madrid", "nation": "🇫🇷", "price": 15000000, "espn_id": 199096, "espn_name": "K. Mbappé"},
        {"id": "fw2",  "name": "Haaland",     "team": "Man City",    "nation": "🇳🇴", "price": 14000000, "espn_id": 255996, "espn_name": "E. Haaland"},
        {"id": "fw3",  "name": "Vinicius Jr", "team": "Real Madrid", "nation": "🇧🇷", "price": 13000000, "espn_id": 272382, "espn_name": "Vinicius Jr."},
        {"id": "fw4",  "name": "Lewandowski", "team": "Barcelona",   "nation": "🇵🇱", "price": 9000000,  "espn_id": 118844, "espn_name": "R. Lewandowski"},
        {"id": "fw5",  "name": "Lautaro",     "team": "Inter",       "nation": "🇦🇷", "price": 10000000, "espn_id": 264786, "espn_name": "L. Martínez"},
        {"id": "fw6",  "name": "Kane",        "team": "Bayern",      "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 12000000, "espn_id": 172695, "espn_name": "H. Kane"},
        {"id": "fw7",  "name": "Havertz",     "team": "Arsenal",     "nation": "🇩🇪", "price": 8000000,  "espn_id": 262973, "espn_name": "K. Havertz"},
        {"id": "fw8",  "name": "Raphinha",    "team": "Barcelona",   "nation": "🇧🇷", "price": 9000000,  "espn_id": 299157, "espn_name": "Raphinha"},
        {"id": "fw9",  "name": "Dembélé",     "team": "PSG",         "nation": "🇫🇷", "price": 8500000,  "espn_id": 232842, "espn_name": "O. Dembélé"},
        {"id": "fw10", "name": "Olise",       "team": "Bayern",      "nation": "🇫🇷", "price": 8000000,  "espn_id": 374028, "espn_name": "M. Olise"},
        {"id": "fw11", "name": "Thuram",      "team": "Inter",       "nation": "🇫🇷", "price": 7500000,  "espn_id": 238820, "espn_name": "M. Thuram"},
        {"id": "fw12", "name": "Nkunku",      "team": "Man City",    "nation": "🇫🇷", "price": 7000000,  "espn_id": 278822, "espn_name": "C. Nkunku"},
    ],
}

# Flat lookups
ALL_PLAYERS: dict = {}
ESPN_ID_MAP: dict = {}   # espn_id → player
ESPN_NAME_MAP: dict = {}  # lowercase espn_name → player

for _pos, _plist in PLAYERS.items():
    for _p in _plist:
        _entry = {**_p, "position": _pos}
        ALL_PLAYERS[_p["id"]] = _entry
        if _p.get("espn_id"):
            ESPN_ID_MAP[_p["espn_id"]] = _entry
        if _p.get("espn_name"):
            ESPN_NAME_MAP[_p["espn_name"].lower()] = _entry
            last = _p["espn_name"].split(".")[-1].strip().lower()
            if last and last not in ESPN_NAME_MAP:
                ESPN_NAME_MAP[last] = _entry


def get_player(player_id: str) -> dict | None:
    return ALL_PLAYERS.get(player_id)


def get_by_position(position: str) -> list:
    return PLAYERS.get(position.upper(), [])


def get_player_by_espn_id(espn_id: int) -> dict | None:
    return ESPN_ID_MAP.get(espn_id)


def get_player_by_espn_name(name: str) -> dict | None:
    if not name:
        return None
    n = name.lower().strip()
    if n in ESPN_NAME_MAP:
        return ESPN_NAME_MAP[n]
    last = n.split(".")[-1].strip()
    if last in ESPN_NAME_MAP:
        return ESPN_NAME_MAP[last]
    for key, p in ESPN_NAME_MAP.items():
        if last and (last in key or key in last):
            return p
    return None


def fmt_price(price: int) -> str:
    return f"€{price / 1_000_000:.1f}M"
