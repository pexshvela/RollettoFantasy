"""
players.py — Official UCL Fantasy 2025/26 player roster.
Prices in euros (millions converted to integers).
espn_name: how the player appears in FlashScore API responses.
"""
import unicodedata


def _normalize(s: str) -> str:
    """Strip accents: Mbappé→Mbappe, Rüdiger→Rudiger etc."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


PLAYERS = {
    "GK": [
        {"id": "gk1",  "name": "Raya",      "team": "Arsenal",      "nation": "🇪🇸", "price": 5600000,  "espn_name": "D. Raya"},
        {"id": "gk2",  "name": "Safanov",   "team": "PSG",          "nation": "🇷🇺", "price": 4600000,  "espn_name": "M. Safonov"},
        {"id": "gk3",  "name": "Neuer",     "team": "Bayern",       "nation": "🇩🇪", "price": 6000000,  "espn_name": "M. Neuer"},
        {"id": "gk4",  "name": "Oblak",     "team": "Atletico",     "nation": "🇸🇮", "price": 5700000,  "espn_name": "J. Oblak"},
        {"id": "gk5",  "name": "Musso",     "team": "Atalanta",     "nation": "🇦🇷", "price": 4600000,  "espn_name": "J. Musso"},
        {"id": "gk6",  "name": "Urbig",     "team": "Leipzig",      "nation": "🇩🇪", "price": 4500000,  "espn_name": "J. Urbig"},
        {"id": "gk7",  "name": "Chevalier", "team": "Lille",        "nation": "🇫🇷", "price": 4400000,  "espn_name": "L. Chevalier"},
        {"id": "gk8",  "name": "Arrizabalaga", "team": "Sporting",  "nation": "🇪🇸", "price": 4500000,  "espn_name": "K. Arrizabalaga"},
        {"id": "gk9",  "name": "Setford",   "team": "Ajax",         "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 4000000,  "espn_name": "T. Setford"},
        {"id": "gk10", "name": "De Luis",   "team": "Brest",        "nation": "🇫🇷", "price": 4000000,  "espn_name": "M. De Luis"},
    ],
    "DEF": [
        {"id": "def1",  "name": "Pacho",       "team": "PSG",          "nation": "🇪🇨", "price": 5100000,  "espn_name": "W. Pacho"},
        {"id": "def2",  "name": "Nuno Mendes", "team": "PSG",          "nation": "🇵🇹", "price": 6400000,  "espn_name": "Nuno Mendes"},
        {"id": "def3",  "name": "Hakimi",      "team": "PSG",          "nation": "🇲🇦", "price": 6000000,  "espn_name": "A. Hakimi"},
        {"id": "def4",  "name": "Gabriel",     "team": "Arsenal",      "nation": "🇧🇷", "price": 5800000,  "espn_name": "Gabriel"},
        {"id": "def5",  "name": "Saliba",      "team": "Arsenal",      "nation": "🇫🇷", "price": 6000000,  "espn_name": "W. Saliba"},
        {"id": "def6",  "name": "White",       "team": "Arsenal",      "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 4700000,  "espn_name": "B. White"},
        {"id": "def7",  "name": "Timber",      "team": "Arsenal",      "nation": "🇳🇱", "price": 4900000,  "espn_name": "J. Timber"},
        {"id": "def8",  "name": "Calafiori",   "team": "Arsenal",      "nation": "🇮🇹", "price": 4600000,  "espn_name": "R. Calafiori"},
        {"id": "def9",  "name": "Lewis-Skelly","team": "Arsenal",      "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 4500000,  "espn_name": "M. Lewis-Skelly"},
        {"id": "def10", "name": "Upamecano",   "team": "Bayern",       "nation": "🇫🇷", "price": 5000000,  "espn_name": "D. Upamecano"},
        {"id": "def11", "name": "Davies",      "team": "Bayern",       "nation": "🇨🇦", "price": 5300000,  "espn_name": "A. Davies"},
        {"id": "def12", "name": "Stanisic",    "team": "Bayern",       "nation": "🇩🇪", "price": 4700000,  "espn_name": "J. Stanisic"},
        {"id": "def13", "name": "Guerreiro",   "team": "Bayern",       "nation": "🇵🇹", "price": 4800000,  "espn_name": "R. Guerreiro"},
        {"id": "def14", "name": "Hincapie",    "team": "Leverkusen",   "nation": "🇪🇨", "price": 4900000,  "espn_name": "P. Hincapie"},
        {"id": "def15", "name": "Tah",         "team": "Leverkusen",   "nation": "🇩🇪", "price": 5400000,  "espn_name": "J. Tah"},
        {"id": "def16", "name": "Hancko",      "team": "Feyenoord",    "nation": "🇸🇰", "price": 4600000,  "espn_name": "D. Hancko"},
        {"id": "def17", "name": "Ruggeri",     "team": "Atalanta",     "nation": "🇦🇷", "price": 4400000,  "espn_name": "M. Ruggeri"},
        {"id": "def18", "name": "Marquinhos",  "team": "PSG",          "nation": "🇧🇷", "price": 5100000,  "espn_name": "Marquinhos"},
        {"id": "def19", "name": "Gimenez",     "team": "Atletico",     "nation": "🇺🇾", "price": 4600000,  "espn_name": "J. Gimenez"},
        {"id": "def20", "name": "Molina",      "team": "Atletico",     "nation": "🇦🇷", "price": 4800000,  "espn_name": "N. Molina"},
        {"id": "def21", "name": "Le Normand",  "team": "Atletico",     "nation": "🇫🇷", "price": 4400000,  "espn_name": "R. Le Normand"},
        {"id": "def22", "name": "Lenglet",     "team": "Atletico",     "nation": "🇫🇷", "price": 4400000,  "espn_name": "C. Lenglet"},
        {"id": "def23", "name": "Mosquera",    "team": "Valencia",     "nation": "🇨🇴", "price": 4200000,  "espn_name": "C. Mosquera"},
        {"id": "def24", "name": "Zabarnyi",    "team": "Bournemouth",  "nation": "🇺🇦", "price": 3800000,  "espn_name": "I. Zabarnyi"},
        {"id": "def25", "name": "Ito",         "team": "Stuttgart",    "nation": "🇯🇵", "price": 3800000,  "espn_name": "H. Ito"},
        {"id": "def26", "name": "L. Hernandez","team": "PSG",          "nation": "🇫🇷", "price": 3800000,  "espn_name": "L. Hernandez"},
        {"id": "def27", "name": "Salmon",      "team": "Brest",        "nation": "🇫🇷", "price": 4000000,  "espn_name": "M. Salmon"},
        {"id": "def28", "name": "Boly",        "team": "Lille",        "nation": "🇨🇮", "price": 4000000,  "espn_name": "D. Boly"},
        {"id": "def29", "name": "Beraldo",     "team": "PSG",          "nation": "🇧🇷", "price": 4000000,  "espn_name": "Lucas Beraldo"},
        {"id": "def30", "name": "Kim",         "team": "Bayern",       "nation": "🇰🇷", "price": 4700000,  "espn_name": "M. Kim"},
        {"id": "def31", "name": "Pubill",      "team": "Almeria",      "nation": "🇪🇸", "price": 3800000,  "espn_name": "M. Pubill"},
    ],
    "MF": [
        {"id": "mf1",  "name": "Kvaratskhelia","team": "PSG",        "nation": "🇬🇪", "price": 8400000,  "espn_name": "K. Kvaratskhelia"},
        {"id": "mf2",  "name": "Vitinha",      "team": "PSG",        "nation": "🇵🇹", "price": 7300000,  "espn_name": "Vitinha"},
        {"id": "mf3",  "name": "Doue",         "team": "PSG",        "nation": "🇫🇷", "price": 8100000,  "espn_name": "D. Doue"},
        {"id": "mf4",  "name": "Zaire-Emery",  "team": "PSG",        "nation": "🇫🇷", "price": 5500000,  "espn_name": "W. Zaire-Emery"},
        {"id": "mf5",  "name": "Barcola",      "team": "PSG",        "nation": "🇫🇷", "price": 7500000,  "espn_name": "B. Barcola"},
        {"id": "mf6",  "name": "Joao Neves",   "team": "PSG",        "nation": "🇵🇹", "price": 6100000,  "espn_name": "Joao Neves"},
        {"id": "mf7",  "name": "Olise",        "team": "Bayern",     "nation": "🇫🇷", "price": 8300000,  "espn_name": "M. Olise"},
        {"id": "mf8",  "name": "Musiala",      "team": "Bayern",     "nation": "🇩🇪", "price": 8900000,  "espn_name": "J. Musiala"},
        {"id": "mf9",  "name": "Gnabry",       "team": "Bayern",     "nation": "🇩🇪", "price": 6500000,  "espn_name": "S. Gnabry"},
        {"id": "mf10", "name": "Kimmich",      "team": "Bayern",     "nation": "🇩🇪", "price": 6300000,  "espn_name": "J. Kimmich"},
        {"id": "mf11", "name": "Goretzka",     "team": "Bayern",     "nation": "🇩🇪", "price": 4900000,  "espn_name": "L. Goretzka"},
        {"id": "mf12", "name": "Laimer",       "team": "Bayern",     "nation": "🇦🇹", "price": 5500000,  "espn_name": "K. Laimer"},
        {"id": "mf13", "name": "Pavlovic",     "team": "Bayern",     "nation": "🇷🇸", "price": 5000000,  "espn_name": "A. Pavlovic"},
        {"id": "mf14", "name": "Rice",         "team": "Arsenal",    "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 7100000,  "espn_name": "D. Rice"},
        {"id": "mf15", "name": "Saka",         "team": "Arsenal",    "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 9500000,  "espn_name": "B. Saka"},
        {"id": "mf16", "name": "Martinelli",   "team": "Arsenal",    "nation": "🇧🇷", "price": 7600000,  "espn_name": "G. Martinelli"},
        {"id": "mf17", "name": "Odegaard",     "team": "Arsenal",    "nation": "🇳🇴", "price": 8400000,  "espn_name": "M. Odegaard"},
        {"id": "mf18", "name": "Trossard",     "team": "Arsenal",    "nation": "🇧🇪", "price": 7000000,  "espn_name": "L. Trossard"},
        {"id": "mf19", "name": "Merino",       "team": "Arsenal",    "nation": "🇪🇸", "price": 6700000,  "espn_name": "M. Merino"},
        {"id": "mf20", "name": "Madueke",      "team": "Chelsea",    "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 6600000,  "espn_name": "N. Madueke"},
        {"id": "mf21", "name": "Eze",          "team": "Crystal P",  "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 7500000,  "espn_name": "E. Eze"},
        {"id": "mf22", "name": "Simone",       "team": "Atletico",   "nation": "🇦🇷", "price": 6200000,  "espn_name": "G. Simeone"},
        {"id": "mf23", "name": "Llorente",     "team": "Atletico",   "nation": "🇪🇸", "price": 6900000,  "espn_name": "M. Llorente"},
        {"id": "mf24", "name": "Griezmann",    "team": "Atletico",   "nation": "🇫🇷", "price": 8600000,  "espn_name": "A. Griezmann"},
        {"id": "mf25", "name": "Koke",         "team": "Atletico",   "nation": "🇪🇸", "price": 5800000,  "espn_name": "Koke"},
        {"id": "mf26", "name": "Barrios",      "team": "Atletico",   "nation": "🇦🇷", "price": 5300000,  "espn_name": "P. Barrios"},
        {"id": "mf27", "name": "Lookman",      "team": "Atalanta",   "nation": "🇳🇬", "price": 7000000,  "espn_name": "A. Lookman"},
        {"id": "mf28", "name": "Zubimendi",    "team": "Arsenal",    "nation": "🇪🇸", "price": 5900000,  "espn_name": "M. Zubimendi"},
        {"id": "mf29", "name": "Baena",        "team": "Villarreal", "nation": "🇪🇸", "price": 4400000,  "espn_name": "Alex Baena"},
        {"id": "mf30", "name": "Karl",         "team": "Lille",      "nation": "🇫🇷", "price": 5200000,  "espn_name": "L. Karl"},
        {"id": "mf31", "name": "Norgaard",     "team": "Brentford",  "nation": "🇩🇰", "price": 4600000,  "espn_name": "C. Norgaard"},
        {"id": "mf32", "name": "Mayulu",       "team": "PSG",        "nation": "🇫🇷", "price": 4200000,  "espn_name": "S. Mayulu"},
        {"id": "mf33", "name": "Fabian Ruiz",  "team": "PSG",        "nation": "🇪🇸", "price": 6300000,  "espn_name": "Fabian Ruiz"},
        {"id": "mf34", "name": "Lee",          "team": "Bayer L",    "nation": "🇰🇷", "price": 5400000,  "espn_name": "K. Lee"},
        {"id": "mf35", "name": "Almada",       "team": "Atletico",   "nation": "🇦🇷", "price": 4600000,  "espn_name": "T. Almada"},
        {"id": "mf36", "name": "Cardoso",      "team": "Atletico",   "nation": "🇵🇹", "price": 4500000,  "espn_name": "J. Cardoso"},
        {"id": "mf37", "name": "Mbaye",        "team": "Feyenoord",  "nation": "🇸🇳", "price": 4800000,  "espn_name": "I. Mbaye"},
        {"id": "mf38", "name": "Dowman",       "team": "Aston V",    "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 5200000,  "espn_name": "M. Dowman"},
        {"id": "mf39", "name": "Mendoza",      "team": "Sporting",   "nation": "🇨🇴", "price": 4800000,  "espn_name": "R. Mendoza"},
        {"id": "mf40", "name": "Dro Fernandez","team": "Atletico",   "nation": "🇦🇷", "price": 4800000,  "espn_name": "Dro Fernandez"},
        {"id": "mf41", "name": "Ibrahim",      "team": "Young Boys", "nation": "🇨🇭", "price": 4500000,  "espn_name": "I. Ibrahim"},
        {"id": "mf42", "name": "Bailey-Joseph","team": "Sporting",   "nation": "🇫🇷", "price": 4500000,  "espn_name": "B. Bailey-Joseph"},
        {"id": "mf43", "name": "Q. Timber",    "team": "Arsenal",    "nation": "🇳🇱", "price": 5500000,  "espn_name": "Q. Timber"},
        {"id": "mf44", "name": "Vargasc",      "team": "Bruges",     "nation": "🇨🇷", "price": 5000000,  "espn_name": "O. Vargas"},
        {"id": "mf45", "name": "Gonzalez",     "team": "Leipzig",    "nation": "🇦🇷", "price": 4700000,  "espn_name": "N. Gonzalez"},
        {"id": "mf46", "name": "Bischof",      "team": "Salzburg",   "nation": "🇨🇭", "price": 5000000,  "espn_name": "T. Bischof"},
    ],
    "FW": [
        {"id": "fw1",  "name": "Kane",       "team": "Bayern",    "nation": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "price": 10900000, "espn_name": "H. Kane"},
        {"id": "fw2",  "name": "J. Alvarez", "team": "Atletico",  "nation": "🇦🇷", "price": 9400000,  "espn_name": "J. Alvarez"},
        {"id": "fw3",  "name": "Gyokeres",   "team": "Sporting",  "nation": "🇸🇪", "price": 9000000,  "espn_name": "V. Gyokeres"},
        {"id": "fw4",  "name": "Dembele",    "team": "PSG",       "nation": "🇫🇷", "price": 9600000,  "espn_name": "O. Dembele"},
        {"id": "fw5",  "name": "Havertz",    "team": "Arsenal",   "nation": "🇩🇪", "price": 7500000,  "espn_name": "K. Havertz"},
        {"id": "fw6",  "name": "Luis Diaz",  "team": "Liverpool", "nation": "🇨🇴", "price": 7800000,  "espn_name": "Luis Diaz"},
        {"id": "fw7",  "name": "Sorloth",    "team": "Atletico",  "nation": "🇳🇴", "price": 7500000,  "espn_name": "A. Sorloth"},
        {"id": "fw8",  "name": "Gonçalo Ramos","team": "PSG",     "nation": "🇵🇹", "price": 6300000,  "espn_name": "Goncalo Ramos"},
        {"id": "fw9",  "name": "Jackson",    "team": "Chelsea",   "nation": "🇸🇳", "price": 7100000,  "espn_name": "N. Jackson"},
        {"id": "fw10", "name": "Jesus",      "team": "Arsenal",   "nation": "🇧🇷", "price": 5700000,  "espn_name": "G. Jesus"},
        {"id": "fw11", "name": "Annous",     "team": "PSG",       "nation": "🇫🇷", "price": 5000000,  "espn_name": "A. Annous"},
        {"id": "fw12", "name": "Ndjantou",   "team": "Sporting",  "nation": "🇨🇲", "price": 5000000,  "espn_name": "Q. Ndjantou"},
        {"id": "fw13", "name": "Mike",       "team": "Feyenoord", "nation": "🇨🇩", "price": 5000000,  "espn_name": "W. Mike"},
    ],
}

# ── Build lookup dicts ────────────────────────────────────────────────────────
ALL_PLAYERS: dict = {}
ESPN_NAME_MAP: dict = {}

for _pos, _plist in PLAYERS.items():
    for _p in _plist:
        _entry = {**_p, "position": _pos}
        ALL_PLAYERS[_p["id"]] = _entry
        if _p.get("espn_name"):
            n = _p["espn_name"]
            ESPN_NAME_MAP[n.lower()] = _entry
            # Also store last name part
            last = n.split(".")[-1].strip().lower()
            if last and last not in ESPN_NAME_MAP:
                ESPN_NAME_MAP[last] = _entry

# Accent-normalized map
_ESPN_NORM_MAP: dict = {_normalize(k): v for k, v in ESPN_NAME_MAP.items()}


def get_player(player_id: str) -> dict | None:
    return ALL_PLAYERS.get(player_id)


def get_by_position(position: str) -> list:
    return PLAYERS.get(position.upper(), [])


def get_player_by_espn_id(espn_id: int) -> dict | None:
    for p in ALL_PLAYERS.values():
        if p.get("espn_id") == espn_id:
            return p
    return None


def get_player_by_espn_name(name: str) -> dict | None:
    if not name:
        return None
    n = name.lower().strip()
    nn = _normalize(n)

    # 1. Direct match
    if n in ESPN_NAME_MAP:
        return ESPN_NAME_MAP[n]
    if nn in _ESPN_NORM_MAP:
        return _ESPN_NORM_MAP[nn]

    # 2. Reversed format: "Olise M." -> "m. olise"
    parts = nn.split()
    if len(parts) == 2:
        rev = parts[1] + " " + parts[0]
        if rev in _ESPN_NORM_MAP:
            return _ESPN_NORM_MAP[rev]

    # 3. Any part longer than 2 chars
    for part in parts:
        part = part.strip(".")
        if len(part) > 2 and part in _ESPN_NORM_MAP:
            return _ESPN_NORM_MAP[part]

    # 4. Partial substring match
    for part in parts:
        part = part.strip(".")
        if len(part) <= 2:
            continue
        for key, p in _ESPN_NORM_MAP.items():
            if part in key or key in part:
                return p

    return None


def fmt_price(price: int) -> str:
    return f"€{price / 1_000_000:.1f}M"
