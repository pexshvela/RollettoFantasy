"""
players.py — Player lists for UCL and PL tournaments.
Switch via active tournament setting.
Prices stored in cents (€5.5m = 5500000) for precision.
"""
import unicodedata
from typing import Optional


def _norm(s: str) -> str:
    """Normalize accents: Dembélé→Dembele, Ødegaard→Odegaard etc."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


# ── UCL Players (Arsenal, PSG, Atletico Madrid, Bayern Munich) ────────────────

UCL_PLAYERS_RAW = [
    # Arsenal
    {"name": "Bukayo Saka",         "team": "Arsenal",  "pos": "MF", "price": 9500000},
    {"name": "Viktor Gyokeres",     "team": "Arsenal",  "pos": "FW", "price": 9000000},
    {"name": "Martin Odegaard",     "team": "Arsenal",  "pos": "MF", "price": 8500000},
    {"name": "Gabriel Martinelli",  "team": "Arsenal",  "pos": "MF", "price": 7500000},
    {"name": "Kai Havertz",         "team": "Arsenal",  "pos": "FW", "price": 7500000},
    {"name": "Eberechi Eze",        "team": "Arsenal",  "pos": "MF", "price": 7500000},
    {"name": "Leandro Trossard",    "team": "Arsenal",  "pos": "MF", "price": 7000000},
    {"name": "Declan Rice",         "team": "Arsenal",  "pos": "MF", "price": 7000000},
    {"name": "Mikel Merino",        "team": "Arsenal",  "pos": "MF", "price": 6500000},
    {"name": "Noni Madueke",        "team": "Arsenal",  "pos": "MF", "price": 6500000},
    {"name": "William Saliba",      "team": "Arsenal",  "pos": "DEF","price": 6000000},
    {"name": "Martin Zubimendi",    "team": "Arsenal",  "pos": "MF", "price": 6000000},
    {"name": "Ethan Nwaneri",       "team": "Arsenal",  "pos": "MF", "price": 5500000},
    {"name": "Max Dowman",          "team": "Arsenal",  "pos": "MF", "price": 5500000},
    {"name": "Gabriel",             "team": "Arsenal",  "pos": "DEF","price": 5500000},
    {"name": "David Raya",          "team": "Arsenal",  "pos": "GK", "price": 5500000},
    {"name": "Ben White",           "team": "Arsenal",  "pos": "DEF","price": 5000000},
    {"name": "Christian Norgaard",  "team": "Arsenal",  "pos": "MF", "price": 5000000},
    {"name": "Piero Hincapie",      "team": "Arsenal",  "pos": "DEF","price": 5000000},
    {"name": "Jurrien Timber",      "team": "Arsenal",  "pos": "DEF","price": 5000000},
    {"name": "Kepa Arrizabalaga",   "team": "Arsenal",  "pos": "GK", "price": 4500000},
    {"name": "Cristhian Mosquera",  "team": "Arsenal",  "pos": "DEF","price": 4500000},
    {"name": "Riccardo Calafiori",  "team": "Arsenal",  "pos": "DEF","price": 4500000},
    {"name": "Myles Lewis-Skelly",  "team": "Arsenal",  "pos": "DEF","price": 4500000},
    {"name": "Tommy Setford",       "team": "Arsenal",  "pos": "GK", "price": 4000000},
    # PSG
    {"name": "Ousmane Dembele",     "team": "PSG",      "pos": "FW", "price": 10000000},
    {"name": "Desire Doue",         "team": "PSG",      "pos": "MF", "price": 8000000},
    {"name": "Khvicha Kvaratskhelia","team": "PSG",     "pos": "MF", "price": 8000000},
    {"name": "Bradley Barcola",     "team": "PSG",      "pos": "MF", "price": 7500000},
    {"name": "Goncalo Ramos",       "team": "PSG",      "pos": "FW", "price": 7000000},
    {"name": "Vitinha",             "team": "PSG",      "pos": "MF", "price": 7000000},
    {"name": "Fabian Ruiz",         "team": "PSG",      "pos": "MF", "price": 6500000},
    {"name": "Nuno Mendes",         "team": "PSG",      "pos": "DEF","price": 6000000},
    {"name": "Achraf Hakimi",       "team": "PSG",      "pos": "DEF","price": 6000000},
    {"name": "Joao Neves",          "team": "PSG",      "pos": "MF", "price": 6000000},
    {"name": "Kang-in Lee",         "team": "PSG",      "pos": "MF", "price": 6000000},
    {"name": "Warren Zaire-Emery",  "team": "PSG",      "pos": "MF", "price": 5500000},
    {"name": "Marquinhos",          "team": "PSG",      "pos": "DEF","price": 5000000},
    {"name": "Willian Pacho",       "team": "PSG",      "pos": "DEF","price": 5000000},
    {"name": "Ibrahim Mbaye",       "team": "PSG",      "pos": "MF", "price": 5000000},
    {"name": "Matvei Safonov",      "team": "PSG",      "pos": "GK", "price": 4500000},
    {"name": "Lucas Chevalier",     "team": "PSG",      "pos": "GK", "price": 4500000},
    {"name": "Senny Mayulu",        "team": "PSG",      "pos": "MF", "price": 4500000},
    {"name": "David Boly",          "team": "PSG",      "pos": "DEF","price": 4000000},
    {"name": "Lucas Hernandez",     "team": "PSG",      "pos": "DEF","price": 4000000},
    {"name": "Lucas Beraldo",       "team": "PSG",      "pos": "DEF","price": 4000000},
    {"name": "Illia Zabarnyi",      "team": "PSG",      "pos": "DEF","price": 4000000},
    {"name": "Martin James",        "team": "PSG",      "pos": "MF", "price": 4000000},
    {"name": "Noham Kamara",        "team": "PSG",      "pos": "DEF","price": 4000000},
    # Atletico Madrid
    {"name": "Julian Alvarez",      "team": "Atletico", "pos": "FW", "price": 9000000},
    {"name": "Antoine Griezmann",   "team": "Atletico", "pos": "FW", "price": 8500000},
    {"name": "Alexander Sorloth",   "team": "Atletico", "pos": "FW", "price": 7500000},
    {"name": "Marcos Llorente",     "team": "Atletico", "pos": "MF", "price": 6500000},
    {"name": "Giuliano Simeone",    "team": "Atletico", "pos": "MF", "price": 6000000},
    {"name": "Giacomo Raspadori",   "team": "Atletico", "pos": "FW", "price": 6000000},
    {"name": "Jan Oblak",           "team": "Atletico", "pos": "GK", "price": 6000000},
    {"name": "Koke",                "team": "Atletico", "pos": "MF", "price": 6000000},
    {"name": "Pablo Barrios",       "team": "Atletico", "pos": "MF", "price": 5500000},
    {"name": "Conor Gallagher",     "team": "Atletico", "pos": "MF", "price": 5500000},
    {"name": "Javier Galan",        "team": "Atletico", "pos": "DEF","price": 5000000},
    {"name": "Carlos Martin",       "team": "Atletico", "pos": "DEF","price": 5000000},
    {"name": "Nicolas Gonzalez",    "team": "Atletico", "pos": "MF", "price": 5000000},
    {"name": "Alex Baena",          "team": "Atletico", "pos": "MF", "price": 5000000},
    {"name": "Thiago Almada",       "team": "Atletico", "pos": "MF", "price": 5000000},
    {"name": "Jose Maria Gimenez",  "team": "Atletico", "pos": "DEF","price": 5000000},
    {"name": "Nahuel Molina",       "team": "Atletico", "pos": "DEF","price": 5000000},
    {"name": "Johnny Cardoso",      "team": "Atletico", "pos": "MF", "price": 4500000},
    {"name": "Juan Musso",          "team": "Atletico", "pos": "GK", "price": 4500000},
    {"name": "Robin Le Normand",    "team": "Atletico", "pos": "DEF","price": 4500000},
    {"name": "Matteo Ruggeri",      "team": "Atletico", "pos": "DEF","price": 4500000},
    {"name": "Clement Lenglet",     "team": "Atletico", "pos": "DEF","price": 4500000},
    {"name": "David Hancko",        "team": "Atletico", "pos": "DEF","price": 4500000},
    {"name": "Mario De Luis",       "team": "Atletico", "pos": "GK", "price": 4000000},
    {"name": "Marc Pubill",         "team": "Atletico", "pos": "DEF","price": 4000000},
    # Bayern Munich
    {"name": "Harry Kane",          "team": "Bayern",   "pos": "FW", "price": 10500000},
    {"name": "Jamal Musiala",       "team": "Bayern",   "pos": "MF", "price": 9000000},
    {"name": "Michael Olise",       "team": "Bayern",   "pos": "MF", "price": 8000000},
    {"name": "Luis Diaz",           "team": "Bayern",   "pos": "FW", "price": 7500000},
    {"name": "Nicolas Jackson",     "team": "Bayern",   "pos": "FW", "price": 7000000},
    {"name": "Joshua Kimmich",      "team": "Bayern",   "pos": "MF", "price": 6500000},
    {"name": "Serge Gnabry",        "team": "Bayern",   "pos": "MF", "price": 6500000},
    {"name": "Manuel Neuer",        "team": "Bayern",   "pos": "GK", "price": 6000000},
    {"name": "Leon Goretzka",       "team": "Bayern",   "pos": "MF", "price": 5500000},
    {"name": "Konrad Laimer",       "team": "Bayern",   "pos": "MF", "price": 5500000},
    {"name": "Tom Bischof",         "team": "Bayern",   "pos": "MF", "price": 5500000},
    {"name": "Jonathan Tah",        "team": "Bayern",   "pos": "DEF","price": 5500000},
    {"name": "Alphonso Davies",     "team": "Bayern",   "pos": "DEF","price": 5500000},
    {"name": "Dayot Upamecano",     "team": "Bayern",   "pos": "DEF","price": 5000000},
    {"name": "Aleksandar Pavlovic", "team": "Bayern",   "pos": "MF", "price": 5000000},
    {"name": "Raphael Guerreiro",   "team": "Bayern",   "pos": "DEF","price": 5000000},
    {"name": "Minjae Kim",          "team": "Bayern",   "pos": "DEF","price": 5000000},
    {"name": "Josip Stanisic",      "team": "Bayern",   "pos": "DEF","price": 4500000},
    {"name": "Jonas Urbig",         "team": "Bayern",   "pos": "GK", "price": 4500000},
    {"name": "Sacha Boey",          "team": "Bayern",   "pos": "DEF","price": 4000000},
    {"name": "Sven Ulreich",        "team": "Bayern",   "pos": "GK", "price": 4000000},
    {"name": "Hiroki Ito",          "team": "Bayern",   "pos": "DEF","price": 4000000},
]

# ── PL Players (all 20 teams) ──────────────────────────────────────────────────

PL_PLAYERS_RAW = [
    # Arsenal
    {"name": "David Raya",           "team": "Arsenal",       "pos": "GK",  "price": 6000000},
    {"name": "Kepa Arrizabalaga",    "team": "Arsenal",       "pos": "GK",  "price": 4000000},
    {"name": "Karl Hein",            "team": "Arsenal",       "pos": "GK",  "price": 4000000},
    {"name": "Tommy Setford",        "team": "Arsenal",       "pos": "GK",  "price": 3900000},
    {"name": "Gabriel",              "team": "Arsenal",       "pos": "DEF", "price": 7100000},
    {"name": "William Saliba",       "team": "Arsenal",       "pos": "DEF", "price": 6100000},
    {"name": "Riccardo Calafiori",   "team": "Arsenal",       "pos": "DEF", "price": 5600000},
    {"name": "Jurrien Timber",       "team": "Arsenal",       "pos": "DEF", "price": 6200000},
    {"name": "Jakub Kiwior",         "team": "Arsenal",       "pos": "DEF", "price": 5400000},
    {"name": "Myles Lewis-Skelly",   "team": "Arsenal",       "pos": "DEF", "price": 5000000},
    {"name": "Ben White",            "team": "Arsenal",       "pos": "DEF", "price": 5100000},
    {"name": "Bukayo Saka",          "team": "Arsenal",       "pos": "MF",  "price": 9800000},
    {"name": "Martin Odegaard",      "team": "Arsenal",       "pos": "MF",  "price": 7800000},
    {"name": "Noni Madueke",         "team": "Arsenal",       "pos": "MF",  "price": 6800000},
    {"name": "Gabriel Martinelli",   "team": "Arsenal",       "pos": "MF",  "price": 6800000},
    {"name": "Leandro Trossard",     "team": "Arsenal",       "pos": "MF",  "price": 6500000},
    {"name": "Declan Rice",          "team": "Arsenal",       "pos": "MF",  "price": 7200000},
    {"name": "Mikel Merino",         "team": "Arsenal",       "pos": "MF",  "price": 5400000},
    {"name": "Ethan Nwaneri",        "team": "Arsenal",       "pos": "MF",  "price": 5000000},
    {"name": "Martin Zubimendi",     "team": "Arsenal",       "pos": "MF",  "price": 5000000},
    {"name": "Christian Norgaard",   "team": "Arsenal",       "pos": "MF",  "price": 5100000},
    {"name": "Kai Havertz",          "team": "Arsenal",       "pos": "FW",  "price": 7300000},
    {"name": "Gabriel Jesus",        "team": "Arsenal",       "pos": "FW",  "price": 6400000},
    {"name": "Eberechi Eze",         "team": "Arsenal",       "pos": "FW",  "price": 7200000},
    {"name": "Viktor Gyokeres",      "team": "Arsenal",       "pos": "FW",  "price": 8800000},
    # Aston Villa
    {"name": "Emiliano Martinez",    "team": "Aston Villa",   "pos": "GK",  "price": 5100000},
    {"name": "Marco Bizot",          "team": "Aston Villa",   "pos": "GK",  "price": 4200000},
    {"name": "Matty Cash",           "team": "Aston Villa",   "pos": "DEF", "price": 4700000},
    {"name": "Ezri Konsa",           "team": "Aston Villa",   "pos": "DEF", "price": 4400000},
    {"name": "Pau Torres",           "team": "Aston Villa",   "pos": "DEF", "price": 4300000},
    {"name": "Lucas Digne",          "team": "Aston Villa",   "pos": "DEF", "price": 4500000},
    {"name": "Ian Maatsen",          "team": "Aston Villa",   "pos": "DEF", "price": 4200000},
    {"name": "Morgan Rogers",        "team": "Aston Villa",   "pos": "MF",  "price": 7400000},
    {"name": "Youri Tielemans",      "team": "Aston Villa",   "pos": "MF",  "price": 5900000},
    {"name": "Leon Bailey",          "team": "Aston Villa",   "pos": "MF",  "price": 5500000},
    {"name": "Amadou Onana",         "team": "Aston Villa",   "pos": "MF",  "price": 4800000},
    {"name": "John McGinn",          "team": "Aston Villa",   "pos": "MF",  "price": 5300000},
    {"name": "Harvey Elliott",       "team": "Aston Villa",   "pos": "MF",  "price": 5100000},
    {"name": "Jadon Sancho",         "team": "Aston Villa",   "pos": "MF",  "price": 5800000},
    {"name": "Ollie Watkins",        "team": "Aston Villa",   "pos": "FW",  "price": 8700000},
    {"name": "Tammy Abraham",        "team": "Aston Villa",   "pos": "FW",  "price": 5800000},
    # Bournemouth
    {"name": "Neto",                 "team": "Bournemouth",   "pos": "GK",  "price": 4500000},
    {"name": "Djordje Petrovic",     "team": "Bournemouth",   "pos": "GK",  "price": 4600000},
    {"name": "Illia Zabarnyi",       "team": "Bournemouth",   "pos": "DEF", "price": 5000000},
    {"name": "Marcos Senesi",        "team": "Bournemouth",   "pos": "DEF", "price": 5200000},
    {"name": "Adrien Truffert",      "team": "Bournemouth",   "pos": "DEF", "price": 4700000},
    {"name": "Justin Kluivert",      "team": "Bournemouth",   "pos": "MF",  "price": 6900000},
    {"name": "Marcus Tavernier",     "team": "Bournemouth",   "pos": "MF",  "price": 5400000},
    {"name": "Ryan Christie",        "team": "Bournemouth",   "pos": "MF",  "price": 4900000},
    {"name": "Alex Scott",           "team": "Bournemouth",   "pos": "MF",  "price": 5100000},
    {"name": "Evanilson",            "team": "Bournemouth",   "pos": "FW",  "price": 6700000},
    {"name": "Enes Unal",            "team": "Bournemouth",   "pos": "FW",  "price": 5400000},
    # Brentford
    {"name": "Caoimhin Kelleher",    "team": "Brentford",     "pos": "GK",  "price": 4800000},
    {"name": "Nathan Collins",       "team": "Brentford",     "pos": "DEF", "price": 4900000},
    {"name": "Sepp van den Berg",    "team": "Brentford",     "pos": "DEF", "price": 4600000},
    {"name": "Kevin Schade",         "team": "Brentford",     "pos": "MF",  "price": 7000000},
    {"name": "Mikkel Damsgaard",     "team": "Brentford",     "pos": "MF",  "price": 5600000},
    {"name": "Fabio Carvalho",       "team": "Brentford",     "pos": "MF",  "price": 4600000},
    {"name": "Vitaly Janelt",        "team": "Brentford",     "pos": "MF",  "price": 4900000},
    {"name": "Igor Thiago",          "team": "Brentford",     "pos": "FW",  "price": 7400000},
    {"name": "Dango Ouattara",       "team": "Brentford",     "pos": "FW",  "price": 5900000},
    # Brighton
    {"name": "Bart Verbruggen",      "team": "Brighton",      "pos": "GK",  "price": 4500000},
    {"name": "Jason Steele",         "team": "Brighton",      "pos": "GK",  "price": 4200000},
    {"name": "Lewis Dunk",           "team": "Brighton",      "pos": "DEF", "price": 4500000},
    {"name": "Jan Paul van Hecke",   "team": "Brighton",      "pos": "DEF", "price": 4600000},
    {"name": "Pervis Estupinan",     "team": "Brighton",      "pos": "DEF", "price": 4500000},
    {"name": "Kaoru Mitoma",         "team": "Brighton",      "pos": "MF",  "price": 6100000},
    {"name": "Georginio Rutter",     "team": "Brighton",      "pos": "MF",  "price": 5600000},
    {"name": "Yankuba Minteh",       "team": "Brighton",      "pos": "MF",  "price": 5500000},
    {"name": "Matt O'Riley",         "team": "Brighton",      "pos": "MF",  "price": 5500000},
    {"name": "Pascal Gross",         "team": "Brighton",      "pos": "MF",  "price": 5500000},
    {"name": "Danny Welbeck",        "team": "Brighton",      "pos": "FW",  "price": 6300000},
    {"name": "Evan Ferguson",        "team": "Brighton",      "pos": "FW",  "price": 5500000},
    # Burnley
    {"name": "Max Weiss",            "team": "Burnley",       "pos": "GK",  "price": 4200000},
    {"name": "Kyle Walker",          "team": "Burnley",       "pos": "DEF", "price": 4400000},
    {"name": "Maxime Esteve",        "team": "Burnley",       "pos": "DEF", "price": 3900000},
    {"name": "Manuel Benson",        "team": "Burnley",       "pos": "MF",  "price": 5400000},
    {"name": "James Ward-Prowse",    "team": "Burnley",       "pos": "MF",  "price": 5600000},
    {"name": "Zian Flemming",        "team": "Burnley",       "pos": "MF",  "price": 5300000},
    {"name": "Zeki Amdouni",         "team": "Burnley",       "pos": "FW",  "price": 4800000},
    {"name": "Lyle Foster",          "team": "Burnley",       "pos": "FW",  "price": 4900000},
    {"name": "Armando Broja",        "team": "Burnley",       "pos": "FW",  "price": 5200000},
    # Chelsea
    {"name": "Filip Jorgensen",      "team": "Chelsea",       "pos": "GK",  "price": 4300000},
    {"name": "Robert Sanchez",       "team": "Chelsea",       "pos": "GK",  "price": 4800000},
    {"name": "Marc Cucurella",       "team": "Chelsea",       "pos": "DEF", "price": 6100000},
    {"name": "Reece James",          "team": "Chelsea",       "pos": "DEF", "price": 5600000},
    {"name": "Levi Colwill",         "team": "Chelsea",       "pos": "DEF", "price": 4700000},
    {"name": "Malo Gusto",           "team": "Chelsea",       "pos": "DEF", "price": 4900000},
    {"name": "Cole Palmer",          "team": "Chelsea",       "pos": "MF",  "price": 10500000},
    {"name": "Pedro Neto",           "team": "Chelsea",       "pos": "MF",  "price": 7000000},
    {"name": "Enzo Fernandez",       "team": "Chelsea",       "pos": "MF",  "price": 6500000},
    {"name": "Estevao Willian",      "team": "Chelsea",       "pos": "MF",  "price": 6400000},
    {"name": "Jamie Bynoe-Gittens",  "team": "Chelsea",       "pos": "MF",  "price": 6000000},
    {"name": "Moisés Caicedo",       "team": "Chelsea",       "pos": "MF",  "price": 5700000},
    {"name": "Joao Pedro",           "team": "Chelsea",       "pos": "FW",  "price": 7700000},
    {"name": "Liam Delap",           "team": "Chelsea",       "pos": "FW",  "price": 6200000},
    {"name": "Nicolas Jackson",      "team": "Chelsea",       "pos": "FW",  "price": 6500000},
    {"name": "Alejandro Garnacho",   "team": "Chelsea",       "pos": "FW",  "price": 6400000},
    # Crystal Palace
    {"name": "Dean Henderson",       "team": "Crystal Palace","pos": "GK",  "price": 5100000},
    {"name": "Daniel Munoz",         "team": "Crystal Palace","pos": "DEF", "price": 5800000},
    {"name": "Maxence Lacroix",      "team": "Crystal Palace","pos": "DEF", "price": 5100000},
    {"name": "Tyrick Mitchell",      "team": "Crystal Palace","pos": "DEF", "price": 5000000},
    {"name": "Ismaila Sarr",         "team": "Crystal Palace","pos": "MF",  "price": 6300000},
    {"name": "Adam Wharton",         "team": "Crystal Palace","pos": "MF",  "price": 5000000},
    {"name": "Brennan Johnson",      "team": "Crystal Palace","pos": "MF",  "price": 6500000},
    {"name": "Yéremy Pino",          "team": "Crystal Palace","pos": "MF",  "price": 5800000},
    {"name": "Jean-Philippe Mateta", "team": "Crystal Palace","pos": "FW",  "price": 7600000},
    {"name": "Eddie Nketiah",        "team": "Crystal Palace","pos": "FW",  "price": 5400000},
    {"name": "Evann Guessand",       "team": "Crystal Palace","pos": "FW",  "price": 6200000},
    {"name": "Jorgen Strand Larsen", "team": "Crystal Palace","pos": "FW",  "price": 5900000},
    # Everton
    {"name": "Jordan Pickford",      "team": "Everton",       "pos": "GK",  "price": 5600000},
    {"name": "Jarrad Branthwaite",   "team": "Everton",       "pos": "DEF", "price": 5300000},
    {"name": "James Tarkowski",      "team": "Everton",       "pos": "DEF", "price": 5700000},
    {"name": "Vitalii Mykolenko",    "team": "Everton",       "pos": "DEF", "price": 4900000},
    {"name": "Jake O'Brien",         "team": "Everton",       "pos": "DEF", "price": 4900000},
    {"name": "Iliman Ndiaye",        "team": "Everton",       "pos": "MF",  "price": 6200000},
    {"name": "Dwight McNeil",        "team": "Everton",       "pos": "MF",  "price": 5500000},
    {"name": "James Garner",         "team": "Everton",       "pos": "MF",  "price": 5300000},
    {"name": "Jack Grealish",        "team": "Everton",       "pos": "MF",  "price": 6300000},
    {"name": "Thierno Barry",        "team": "Everton",       "pos": "FW",  "price": 5700000},
    {"name": "Tyler Dibling",        "team": "Everton",       "pos": "MF",  "price": 5300000},
    # Fulham
    {"name": "Bernd Leno",           "team": "Fulham",        "pos": "GK",  "price": 4900000},
    {"name": "Antonee Robinson",     "team": "Fulham",        "pos": "DEF", "price": 4900000},
    {"name": "Joachim Andersen",     "team": "Fulham",        "pos": "DEF", "price": 4500000},
    {"name": "Calvin Bassey",        "team": "Fulham",        "pos": "DEF", "price": 4400000},
    {"name": "Alex Iwobi",           "team": "Fulham",        "pos": "MF",  "price": 6300000},
    {"name": "Emile Smith Rowe",     "team": "Fulham",        "pos": "MF",  "price": 5600000},
    {"name": "Harry Wilson",         "team": "Fulham",        "pos": "MF",  "price": 6000000},
    {"name": "Andreas Pereira",      "team": "Fulham",        "pos": "MF",  "price": 5300000},
    {"name": "Raul Jimenez",         "team": "Fulham",        "pos": "FW",  "price": 6100000},
    {"name": "Rodrigo Muniz",        "team": "Fulham",        "pos": "FW",  "price": 5300000},
    {"name": "Samuel Chukwueze",     "team": "Fulham",        "pos": "MF",  "price": 5300000},
    # Leeds
    {"name": "Illan Meslier",        "team": "Leeds",         "pos": "GK",  "price": 4100000},
    {"name": "Pascal Struijk",       "team": "Leeds",         "pos": "DEF", "price": 4300000},
    {"name": "Jayden Bogle",         "team": "Leeds",         "pos": "DEF", "price": 4400000},
    {"name": "Brenden Aaronson",     "team": "Leeds",         "pos": "MF",  "price": 5400000},
    {"name": "Wilfried Gnonto",      "team": "Leeds",         "pos": "MF",  "price": 5100000},
    {"name": "Daniel James",         "team": "Leeds",         "pos": "MF",  "price": 5200000},
    {"name": "Patrick Bamford",      "team": "Leeds",         "pos": "FW",  "price": 4900000},
    {"name": "Mateo Joseph",         "team": "Leeds",         "pos": "FW",  "price": 5000000},
    {"name": "Dominic Calvert-Lewin","team": "Leeds",         "pos": "FW",  "price": 5700000},
    # Liverpool
    {"name": "Alisson Becker",       "team": "Liverpool",     "pos": "GK",  "price": 5400000},
    {"name": "Giorgi Mamardashvili", "team": "Liverpool",     "pos": "GK",  "price": 4100000},
    {"name": "Jeremie Frimpong",     "team": "Liverpool",     "pos": "DEF", "price": 5700000},
    {"name": "Andrew Robertson",     "team": "Liverpool",     "pos": "DEF", "price": 5700000},
    {"name": "Virgil van Dijk",      "team": "Liverpool",     "pos": "DEF", "price": 6200000},
    {"name": "Ibrahima Konate",      "team": "Liverpool",     "pos": "DEF", "price": 5500000},
    {"name": "Conor Bradley",        "team": "Liverpool",     "pos": "DEF", "price": 4900000},
    {"name": "Mohamed Salah",        "team": "Liverpool",     "pos": "MF",  "price": 14000000},
    {"name": "Florian Wirtz",        "team": "Liverpool",     "pos": "MF",  "price": 8300000},
    {"name": "Luis Diaz",            "team": "Liverpool",     "pos": "MF",  "price": 8000000},
    {"name": "Cody Gakpo",           "team": "Liverpool",     "pos": "MF",  "price": 7300000},
    {"name": "Alexis Mac Allister",  "team": "Liverpool",     "pos": "MF",  "price": 6300000},
    {"name": "Dominik Szoboszlai",   "team": "Liverpool",     "pos": "MF",  "price": 7100000},
    {"name": "Ryan Gravenberch",     "team": "Liverpool",     "pos": "MF",  "price": 5500000},
    {"name": "Darwin Nunez",         "team": "Liverpool",     "pos": "FW",  "price": 6500000},
    {"name": "Alexander Isak",       "team": "Liverpool",     "pos": "FW",  "price": 10300000},
    {"name": "Hugo Ekitike",         "team": "Liverpool",     "pos": "FW",  "price": 9100000},
    # Man City
    {"name": "Ederson",              "team": "Man City",      "pos": "GK",  "price": 5300000},
    {"name": "Rayan Ait-Nouri",      "team": "Man City",      "pos": "DEF", "price": 5700000},
    {"name": "Josko Gvardiol",       "team": "Man City",      "pos": "DEF", "price": 5800000},
    {"name": "Manuel Akanji",        "team": "Man City",      "pos": "DEF", "price": 5400000},
    {"name": "Ruben Dias",           "team": "Man City",      "pos": "DEF", "price": 5500000},
    {"name": "Rico Lewis",           "team": "Man City",      "pos": "DEF", "price": 4600000},
    {"name": "Omar Marmoush",        "team": "Man City",      "pos": "MF",  "price": 8300000},
    {"name": "Phil Foden",           "team": "Man City",      "pos": "MF",  "price": 8000000},
    {"name": "Savinho",              "team": "Man City",      "pos": "MF",  "price": 6900000},
    {"name": "Bernardo Silva",       "team": "Man City",      "pos": "MF",  "price": 6200000},
    {"name": "Rayan Cherki",         "team": "Man City",      "pos": "MF",  "price": 6400000},
    {"name": "Jeremy Doku",          "team": "Man City",      "pos": "MF",  "price": 6400000},
    {"name": "Ilkay Gundogan",       "team": "Man City",      "pos": "MF",  "price": 6300000},
    {"name": "Rodri",                "team": "Man City",      "pos": "MF",  "price": 6300000},
    {"name": "Antoine Semenyo",      "team": "Man City",      "pos": "FW",  "price": 8200000},
    {"name": "Erling Haaland",       "team": "Man City",      "pos": "FW",  "price": 14500000},
    # Man Utd
    {"name": "Andre Onana",          "team": "Man Utd",       "pos": "GK",  "price": 4900000},
    {"name": "Matthijs de Ligt",     "team": "Man Utd",       "pos": "DEF", "price": 4900000},
    {"name": "Lisandro Martinez",    "team": "Man Utd",       "pos": "DEF", "price": 4800000},
    {"name": "Noussair Mazraoui",    "team": "Man Utd",       "pos": "DEF", "price": 4900000},
    {"name": "Diogo Dalot",          "team": "Man Utd",       "pos": "DEF", "price": 4600000},
    {"name": "Patrick Dorgu",        "team": "Man Utd",       "pos": "DEF", "price": 4100000},
    {"name": "Bruno Fernandes",      "team": "Man Utd",       "pos": "MF",  "price": 10300000},
    {"name": "Matheus Cunha",        "team": "Man Utd",       "pos": "MF",  "price": 8000000},
    {"name": "Marcus Rashford",      "team": "Man Utd",       "pos": "MF",  "price": 7000000},
    {"name": "Amad Diallo",          "team": "Man Utd",       "pos": "MF",  "price": 6200000},
    {"name": "Kobbie Mainoo",        "team": "Man Utd",       "pos": "MF",  "price": 4700000},
    {"name": "Bryan Mbeumo",         "team": "Man Utd",       "pos": "FW",  "price": 8500000},
    {"name": "Rasmus Hojlund",       "team": "Man Utd",       "pos": "FW",  "price": 6300000},
    {"name": "Benjamin Sesko",       "team": "Man Utd",       "pos": "FW",  "price": 7300000},
    # Newcastle
    {"name": "Nick Pope",            "team": "Newcastle",     "pos": "GK",  "price": 5000000},
    {"name": "Lewis Hall",           "team": "Newcastle",     "pos": "DEF", "price": 5400000},
    {"name": "Fabian Schar",         "team": "Newcastle",     "pos": "DEF", "price": 5200000},
    {"name": "Dan Burn",             "team": "Newcastle",     "pos": "DEF", "price": 5000000},
    {"name": "Tino Livramento",      "team": "Newcastle",     "pos": "DEF", "price": 4900000},
    {"name": "Jacob Ramsey",         "team": "Newcastle",     "pos": "MF",  "price": 5300000},
    {"name": "Yoane Wissa",          "team": "Newcastle",     "pos": "FW",  "price": 7300000},
    {"name": "Alexander Isak",       "team": "Newcastle",     "pos": "FW",  "price": 10300000},
    # Nottm Forest
    {"name": "Matz Sels",            "team": "Nottm Forest",  "pos": "GK",  "price": 5000000},
    {"name": "Ola Aina",             "team": "Nottm Forest",  "pos": "DEF", "price": 4900000},
    {"name": "Murillo",              "team": "Nottm Forest",  "pos": "DEF", "price": 5100000},
    {"name": "Nikola Milenkovic",    "team": "Nottm Forest",  "pos": "DEF", "price": 4700000},
    {"name": "Anthony Elanga",       "team": "Nottm Forest",  "pos": "MF",  "price": 6000000},
    {"name": "Morgan Gibbs-White",   "team": "Nottm Forest",  "pos": "MF",  "price": 6300000},
    {"name": "Chris Wood",           "team": "Nottm Forest",  "pos": "FW",  "price": 6700000},
    {"name": "Taiwo Awoniyi",        "team": "Nottm Forest",  "pos": "FW",  "price": 5800000},
    # Southampton
    {"name": "Aaron Ramsdale",       "team": "Southampton",   "pos": "GK",  "price": 4500000},
    {"name": "Jan Bednarek",         "team": "Southampton",   "pos": "DEF", "price": 4300000},
    {"name": "Kyle Walker-Peters",   "team": "Southampton",   "pos": "DEF", "price": 4500000},
    {"name": "Stuart Armstrong",     "team": "Southampton",   "pos": "MF",  "price": 4700000},
    {"name": "Cameron Archer",       "team": "Southampton",   "pos": "FW",  "price": 5200000},
    # Spurs
    {"name": "Guglielmo Vicario",    "team": "Spurs",         "pos": "GK",  "price": 5000000},
    {"name": "Pedro Porro",          "team": "Spurs",         "pos": "DEF", "price": 5700000},
    {"name": "Cristian Romero",      "team": "Spurs",         "pos": "DEF", "price": 5500000},
    {"name": "Micky van de Ven",     "team": "Spurs",         "pos": "DEF", "price": 5200000},
    {"name": "Heung-Min Son",        "team": "Spurs",         "pos": "MF",  "price": 6400000},
    {"name": "James Maddison",       "team": "Spurs",         "pos": "MF",  "price": 6400000},
    {"name": "Brennan Johnson",      "team": "Spurs",         "pos": "MF",  "price": 6500000},
    {"name": "Dejan Kulusevski",     "team": "Spurs",         "pos": "MF",  "price": 6700000},
    {"name": "Dominic Solanke",      "team": "Spurs",         "pos": "FW",  "price": 7500000},
    {"name": "Richarlison",          "team": "Spurs",         "pos": "FW",  "price": 5700000},
    # West Ham
    {"name": "Lukasz Fabianski",     "team": "West Ham",      "pos": "GK",  "price": 4200000},
    {"name": "Aaron Wan-Bissaka",    "team": "West Ham",      "pos": "DEF", "price": 4500000},
    {"name": "Kurt Zouma",           "team": "West Ham",      "pos": "DEF", "price": 4400000},
    {"name": "Emerson Palmieri",     "team": "West Ham",      "pos": "DEF", "price": 4300000},
    {"name": "Jarrod Bowen",         "team": "West Ham",      "pos": "MF",  "price": 7300000},
    {"name": "Mohammed Kudus",       "team": "West Ham",      "pos": "MF",  "price": 6700000},
    {"name": "Lucas Paqueta",        "team": "West Ham",      "pos": "MF",  "price": 6200000},
    {"name": "Crysencio Summerville","team": "West Ham",      "pos": "MF",  "price": 6500000},
    {"name": "Michail Antonio",      "team": "West Ham",      "pos": "FW",  "price": 5500000},
    # Wolves
    {"name": "Jose Sa",              "team": "Wolves",        "pos": "GK",  "price": 4600000},
    {"name": "Nelson Semedo",        "team": "Wolves",        "pos": "DEF", "price": 4700000},
    {"name": "Max Kilman",           "team": "Wolves",        "pos": "DEF", "price": 4500000},
    {"name": "Rayan Ait-Nouri",      "team": "Wolves",        "pos": "DEF", "price": 5200000},
    {"name": "Matheus Cunha",        "team": "Wolves",        "pos": "MF",  "price": 7500000},
    {"name": "Pedro Neto",           "team": "Wolves",        "pos": "MF",  "price": 6500000},
    {"name": "Hwang Hee-chan",       "team": "Wolves",        "pos": "FW",  "price": 5800000},
    {"name": "Jorgen Strand Larsen", "team": "Wolves",        "pos": "FW",  "price": 5900000},
]


def _build_lookup(raw_list: list) -> tuple[dict, dict, dict]:
    """Build ALL_PLAYERS dict, name→player map, norm_name→player map."""
    all_players = {}
    name_map    = {}
    norm_map    = {}

    for i, p in enumerate(raw_list):
        pid = f"{p['pos'].lower()}_{i:03d}"
        entry = {
            "id":       pid,
            "name":     p["name"],
            "team":     p["team"],
            "position": p["pos"],
            "price":    p["price"],
        }
        all_players[pid] = entry

        # Name lookups
        nl = p["name"].lower()
        nn = _norm(p["name"])
        name_map[nl] = entry
        norm_map[nn] = entry

        # Also last name
        parts = nl.split()
        if parts:
            last = parts[-1]
            if last not in name_map:
                name_map[last] = entry
            nn_last = _norm(last)
            if nn_last not in norm_map:
                norm_map[nn_last] = entry

    return all_players, name_map, norm_map


# Build both lookups
_UCL_ALL, _UCL_NAME, _UCL_NORM = _build_lookup(UCL_PLAYERS_RAW)
_PL_ALL,  _PL_NAME,  _PL_NORM  = _build_lookup(PL_PLAYERS_RAW)

# Active tournament (set at runtime by sheets.get_setting)
_active = "ucl"


def set_active_tournament(t: str):
    global _active
    _active = t.lower()


def get_all_players() -> dict:
    return _UCL_ALL if _active == "ucl" else _PL_ALL


def get_player(pid: str) -> Optional[dict]:
    return get_all_players().get(pid)


def get_players_by_position(pos: str) -> list:
    return [p for p in get_all_players().values() if p["position"] == pos.upper()]


def find_player_by_name(name: str) -> Optional[dict]:
    """Find player by name — handles accents and surname-first formats."""
    if not name:
        return None
    name_map = _UCL_NAME if _active == "ucl" else _PL_NAME
    norm_map = _UCL_NORM if _active == "ucl" else _PL_NORM

    nl = name.lower().strip()
    nn = _norm(name)

    # Direct match
    if nl in name_map: return name_map[nl]
    if nn in norm_map: return norm_map[nn]

    # Try reversed: "Kane H." → "h. kane"
    parts = nn.split()
    if len(parts) == 2:
        rev = parts[1] + " " + parts[0]
        if rev in norm_map: return norm_map[rev]

    # Partial match on any part > 2 chars
    for part in parts:
        part = part.strip(".")
        if len(part) > 2:
            if part in norm_map: return norm_map[part]
            for key, p in norm_map.items():
                if part in key or key in part:
                    return p
    return None


def fmt_price(price: int) -> str:
    return f"€{price / 1_000_000:.1f}m"


def mask_username(username: str) -> str:
    """Show first and last char, mask middle: 'player' → 'p****r'"""
    if len(username) <= 2:
        return username[0] + "*"
    return username[0] + "*" * (len(username) - 2) + username[-1]
