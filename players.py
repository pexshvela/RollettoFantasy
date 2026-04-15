# Filler player data — replace prices when real data is confirmed

PLAYERS = {
    "GK": [
        {"id": "gk1",  "name": "Alisson",      "team": "Liverpool",   "nation": "🇧🇷", "price": 7000000},
        {"id": "gk2",  "name": "Ter Stegen",   "team": "Barcelona",   "nation": "🇩🇪", "price": 6000000},
        {"id": "gk3",  "name": "Ederson",      "team": "Man City",    "nation": "🇧🇷", "price": 6500000},
        {"id": "gk4",  "name": "Courtois",     "team": "Real Madrid", "nation": "🇧🇪", "price": 7500000},
        {"id": "gk5",  "name": "Donnarumma",   "team": "PSG",         "nation": "🇮🇹", "price": 6000000},
        {"id": "gk6",  "name": "Sommer",       "team": "Inter",       "nation": "🇨🇭", "price": 5000000},
        {"id": "gk7",  "name": "Neuer",        "team": "Bayern",      "nation": "🇩🇪", "price": 5500000},
        {"id": "gk8",  "name": "Raya",         "team": "Arsenal",     "nation": "🇪🇸", "price": 5500000},
    ],
    "DEF": [
        {"id": "def1",  "name": "Van Dijk",         "team": "Liverpool",   "nation": "🇳🇱", "price": 8000000},
        {"id": "def2",  "name": "Alexander-Arnold", "team": "Real Madrid", "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 8500000},
        {"id": "def3",  "name": "Rüdiger",          "team": "Real Madrid", "nation": "🇩🇪", "price": 7000000},
        {"id": "def4",  "name": "Robertson",        "team": "Liverpool",   "nation": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "price": 6000000},
        {"id": "def5",  "name": "Militão",          "team": "Real Madrid", "nation": "🇧🇷", "price": 7500000},
        {"id": "def6",  "name": "Hakimi",           "team": "PSG",         "nation": "🇲🇦", "price": 8000000},
        {"id": "def7",  "name": "T. Hernandez",     "team": "Bayern",      "nation": "🇫🇷", "price": 7000000},
        {"id": "def8",  "name": "Pavard",           "team": "Inter",       "nation": "🇫🇷", "price": 6000000},
        {"id": "def9",  "name": "Upamecano",        "team": "Bayern",      "nation": "🇫🇷", "price": 6000000},
        {"id": "def10", "name": "Saliba",           "team": "Arsenal",     "nation": "🇫🇷", "price": 7500000},
        {"id": "def11", "name": "White",            "team": "Arsenal",     "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 6000000},
        {"id": "def12", "name": "Koundé",           "team": "Barcelona",   "nation": "🇫🇷", "price": 7000000},
        {"id": "def13", "name": "Balde",            "team": "Barcelona",   "nation": "🇪🇸", "price": 5500000},
        {"id": "def14", "name": "Gvardiol",         "team": "Man City",    "nation": "🇭🇷", "price": 7000000},
        {"id": "def15", "name": "Stones",           "team": "Man City",    "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 6000000},
        {"id": "def16", "name": "Bastoni",          "team": "Inter",       "nation": "🇮🇹", "price": 7000000},
    ],
    "MF": [
        {"id": "mf1",  "name": "Bellingham",  "team": "Real Madrid", "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 12000000},
        {"id": "mf2",  "name": "De Bruyne",   "team": "Man City",    "nation": "🇧🇪", "price": 9000000},
        {"id": "mf3",  "name": "Pedri",       "team": "Barcelona",   "nation": "🇪🇸", "price": 9000000},
        {"id": "mf4",  "name": "Rodri",       "team": "Man City",    "nation": "🇪🇸", "price": 8000000},
        {"id": "mf5",  "name": "Vitinha",     "team": "PSG",         "nation": "🇵🇹", "price": 7000000},
        {"id": "mf6",  "name": "Rice",        "team": "Arsenal",     "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 9000000},
        {"id": "mf7",  "name": "Modric",      "team": "Real Madrid", "nation": "🇭🇷", "price": 6000000},
        {"id": "mf8",  "name": "Gündogan",    "team": "Barcelona",   "nation": "🇩🇪", "price": 6500000},
        {"id": "mf9",  "name": "Calhanoglu",  "team": "Inter",       "nation": "🇹🇷", "price": 7000000},
        {"id": "mf10", "name": "Musiala",     "team": "Bayern",      "nation": "🇩🇪", "price": 10000000},
        {"id": "mf11", "name": "Ødegaard",    "team": "Arsenal",     "nation": "🇳🇴", "price": 9000000},
        {"id": "mf12", "name": "Barella",     "team": "Inter",       "nation": "🇮🇹", "price": 7500000},
        {"id": "mf13", "name": "Kimmich",     "team": "Bayern",      "nation": "🇩🇪", "price": 7500000},
        {"id": "mf14", "name": "Saka",        "team": "Arsenal",     "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 10000000},
        {"id": "mf15", "name": "Yamal",       "team": "Barcelona",   "nation": "🇪🇸", "price": 11000000},
    ],
    "FW": [
        {"id": "fw1",  "name": "Mbappé",      "team": "Real Madrid", "nation": "🇫🇷", "price": 15000000},
        {"id": "fw2",  "name": "Haaland",     "team": "Man City",    "nation": "🇳🇴", "price": 14000000},
        {"id": "fw3",  "name": "Vinicius Jr", "team": "Real Madrid", "nation": "🇧🇷", "price": 13000000},
        {"id": "fw4",  "name": "Lewandowski", "team": "Barcelona",   "nation": "🇵🇱", "price": 9000000},
        {"id": "fw5",  "name": "Lautaro",     "team": "Inter",       "nation": "🇦🇷", "price": 10000000},
        {"id": "fw6",  "name": "Kane",        "team": "Bayern",      "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 12000000},
        {"id": "fw7",  "name": "Havertz",     "team": "Arsenal",     "nation": "🇩🇪", "price": 8000000},
        {"id": "fw8",  "name": "Raphinha",    "team": "Barcelona",   "nation": "🇧🇷", "price": 9000000},
        {"id": "fw9",  "name": "Dembélé",     "team": "PSG",         "nation": "🇫🇷", "price": 8500000},
        {"id": "fw10", "name": "Olise",       "team": "Bayern",      "nation": "🇫🇷", "price": 8000000},
        {"id": "fw11", "name": "Thuram",      "team": "Inter",       "nation": "🇫🇷", "price": 7500000},
        {"id": "fw12", "name": "Nkunku",      "team": "Man City",    "nation": "🇫🇷", "price": 7000000},
    ],
}

# Flat lookup dict by player id
ALL_PLAYERS: dict = {}
for _pos, _plist in PLAYERS.items():
    for _p in _plist:
        ALL_PLAYERS[_p["id"]] = {**_p, "position": _pos}


def get_player(player_id: str) -> dict | None:
    return ALL_PLAYERS.get(player_id)


def get_by_position(position: str) -> list:
    return PLAYERS.get(position.upper(), [])


def fmt_price(price: int) -> str:
    return f"€{price / 1_000_000:.1f}M"
