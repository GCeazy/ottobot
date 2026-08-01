# ==============================================================================
# VERSION: 0.4.4
# LINES CHANGED: ~20 lines modified
# CHANGELOG:
# - Incremented patch version to 0.4.4.
# - Added `typing.TypedDict` to explicitly define the `CFLEvent` structure.
# - This resolves strict type-checking diagnostics where Pyright/MyPy panics
#   over mixed types (str, int, datetime) inside the dynamically generated dictionary.
# ==============================================================================

"""!score — get live sports scores and game slates via real-time APIs."""

import urllib.request
import urllib.parse
import json
import asyncio
import gzip
from datetime import datetime, timedelta
from typing import TypedDict
from ottobot import Context, command


class CFLEvent(TypedDict):
    month: int
    day: int
    time_str: str
    away: str
    home: str
    away_name: str
    home_name: str
    away_score: int
    home_score: int
    status: str
    dt: datetime


# League Router Map
LEAGUE_MAP = {
    # ESPN Standard Leagues
    "mlb": ("espn", "baseball", "mlb", "MLB"),
    "nhl": ("espn", "hockey", "nhl", "NHL"),
    "nba": ("espn", "basketball", "nba", "NBA"),
    "nfl": ("espn", "football", "nfl", "NFL"),
    "wnba": ("espn", "basketball", "wnba", "WNBA"),
    "pwhl": ("espn", "hockey", "pwhl", "PWHL"),
    "mls": ("espn", "soccer", "usa.1", "MLS"),
    "epl": ("espn", "soccer", "eng.1", "EPL"),
    "laliga": ("espn", "soccer", "esp.1", "La Liga"),
    "bundesliga": ("espn", "soccer", "ger.1", "Bundesliga"),
    # Custom Dynamic JSON Fetcher
    "cfl": ("ha_cfl", "cfl", "CFL"),
    # Paused Minor Leagues
    "ohl": ("disabled", "", "OHL"),
    "cebl": ("disabled", "", "CEBL"),
    "cpl": ("disabled", "", "CPL"),
    "nll": ("disabled", "", "NLL"),
}

VALID_LEAGUES = sorted(list(LEAGUE_MAP.keys()) + ["f1"])

# Ambiguous triggers
AMBIGUOUS_MAP = {
    "giants": "Try using: ny giants or sf giants",
    "jets": "Try using: ny jets or nhl jets",
    "rangers": "Try using: nhl rangers or texas (rangers)",
    "kings": "Try using: nba kings or nhl kings",
    "cardinals": "Try using: nfl cardinals or stl cardinals",
    "atletico": "Try using: atletico madrid or atletico ottawa",
    "lions": "Try using: bc lions or detroit lions",
}

# Team Router Map
TEAM_MAP = {
    # === BASEBALL (MLB) ===
    "jays": ("espn", "baseball", "mlb", "Blue Jays", "MLB"),
    "blue jays": ("espn", "baseball", "mlb", "Blue Jays", "MLB"),
    "orioles": ("espn", "baseball", "mlb", "Orioles", "MLB"),
    "os": ("espn", "baseball", "mlb", "Orioles", "MLB"),
    "baltimore": ("espn", "baseball", "mlb", "Orioles", "MLB"),
    "red sox": ("espn", "baseball", "mlb", "Red Sox", "MLB"),
    "boston": ("espn", "baseball", "mlb", "Red Sox", "MLB"),
    "yankees": ("espn", "baseball", "mlb", "Yankees", "MLB"),
    "nyy": ("espn", "baseball", "mlb", "Yankees", "MLB"),
    "rays": ("espn", "baseball", "mlb", "Rays", "MLB"),
    "tampa bay": ("espn", "baseball", "mlb", "Rays", "MLB"),
    "white sox": ("espn", "baseball", "mlb", "White Sox", "MLB"),
    "chicago white sox": ("espn", "baseball", "mlb", "White Sox", "MLB"),
    "guardians": ("espn", "baseball", "mlb", "Guardians", "MLB"),
    "cleveland": ("espn", "baseball", "mlb", "Guardians", "MLB"),
    "tigers": ("espn", "baseball", "mlb", "Tigers", "MLB"),
    "detroit": ("espn", "baseball", "mlb", "Tigers", "MLB"),
    "royals": ("espn", "baseball", "mlb", "Royals", "MLB"),
    "kc": ("espn", "baseball", "mlb", "Royals", "MLB"),
    "twins": ("espn", "baseball", "mlb", "Twins", "MLB"),
    "minnesota": ("espn", "baseball", "mlb", "Twins", "MLB"),
    "astros": ("espn", "baseball", "mlb", "Astros", "MLB"),
    "houston": ("espn", "baseball", "mlb", "Astros", "MLB"),
    "angels": ("espn", "baseball", "mlb", "Angels", "MLB"),
    "laa": ("espn", "baseball", "mlb", "Angels", "MLB"),
    "athletics": ("espn", "baseball", "mlb", "Athletics", "MLB"),
    "as": ("espn", "baseball", "mlb", "Athletics", "MLB"),
    "mariners": ("espn", "baseball", "mlb", "Mariners", "MLB"),
    "seattle": ("espn", "baseball", "mlb", "Mariners", "MLB"),
    "texas": ("espn", "baseball", "mlb", "Rangers", "MLB"),
    "texas rangers": ("espn", "baseball", "mlb", "Rangers", "MLB"),
    "braves": ("espn", "baseball", "mlb", "Braves", "MLB"),
    "atlanta": ("espn", "baseball", "mlb", "Braves", "MLB"),
    "marlins": ("espn", "baseball", "mlb", "Marlins", "MLB"),
    "miami": ("espn", "baseball", "mlb", "Marlins", "MLB"),
    "mets": ("espn", "baseball", "mlb", "Mets", "MLB"),
    "nym": ("espn", "baseball", "mlb", "Mets", "MLB"),
    "phillies": ("espn", "baseball", "mlb", "Phillies", "MLB"),
    "philly": ("espn", "baseball", "mlb", "Phillies", "MLB"),
    "nationals": ("espn", "baseball", "mlb", "Nationals", "MLB"),
    "nats": ("espn", "baseball", "mlb", "Nationals", "MLB"),
    "cubs": ("espn", "baseball", "mlb", "Cubs", "MLB"),
    "chicago cubs": ("espn", "baseball", "mlb", "Cubs", "MLB"),
    "reds": ("espn", "baseball", "mlb", "Reds", "MLB"),
    "cincinnati": ("espn", "baseball", "mlb", "Reds", "MLB"),
    "brewers": ("espn", "baseball", "mlb", "Brewers", "MLB"),
    "milwaukee": ("espn", "baseball", "mlb", "Brewers", "MLB"),
    "pirates": ("espn", "baseball", "mlb", "Pirates", "MLB"),
    "pittsburgh": ("espn", "baseball", "mlb", "Pirates", "MLB"),
    "stl cardinals": ("espn", "baseball", "mlb", "Cardinals", "MLB"),
    "mlb cards": ("espn", "baseball", "mlb", "Cardinals", "MLB"),
    "diamondbacks": ("espn", "baseball", "mlb", "Diamondbacks", "MLB"),
    "dbacks": ("espn", "baseball", "mlb", "Diamondbacks", "MLB"),
    "rockies": ("espn", "baseball", "mlb", "Rockies", "MLB"),
    "colorado": ("espn", "baseball", "mlb", "Rockies", "MLB"),
    "dodgers": ("espn", "baseball", "mlb", "Dodgers", "MLB"),
    "lad": ("espn", "baseball", "mlb", "Dodgers", "MLB"),
    "padres": ("espn", "baseball", "mlb", "Padres", "MLB"),
    "san diego": ("espn", "baseball", "mlb", "Padres", "MLB"),
    "sf giants": ("espn", "baseball", "mlb", "Giants", "MLB"),
    "mlb giants": ("espn", "baseball", "mlb", "Giants", "MLB"),
    # === HOCKEY (NHL) ===
    "sens": ("espn", "hockey", "nhl", "Senators", "NHL"),
    "senators": ("espn", "hockey", "nhl", "Senators", "NHL"),
    "ottawa senators": ("espn", "hockey", "nhl", "Senators", "NHL"),
    "leafs": ("espn", "hockey", "nhl", "Maple Leafs", "NHL"),
    "maple leafs": ("espn", "hockey", "nhl", "Maple Leafs", "NHL"),
    "toronto maple leafs": ("espn", "hockey", "nhl", "Maple Leafs", "NHL"),
    "leafs suck": ("espn", "hockey", "nhl", "Maple Leafs", "NHL"),
    "habs": ("espn", "hockey", "nhl", "Canadiens", "NHL"),
    "canadiens": ("espn", "hockey", "nhl", "Canadiens", "NHL"),
    "montreal": ("espn", "hockey", "nhl", "Canadiens", "NHL"),
    "bruins": ("espn", "hockey", "nhl", "Bruins", "NHL"),
    "sabres": ("espn", "hockey", "nhl", "Sabres", "NHL"),
    "red wings": ("espn", "hockey", "nhl", "Red Wings", "NHL"),
    "panthers": ("espn", "hockey", "nhl", "Panthers", "NHL"),
    "nhl panthers": ("espn", "hockey", "nhl", "Panthers", "NHL"),
    "lightning": ("espn", "hockey", "nhl", "Lightning", "NHL"),
    "bolts": ("espn", "hockey", "nhl", "Lightning", "NHL"),
    "hurricanes": ("espn", "hockey", "nhl", "Hurricanes", "NHL"),
    "canes": ("espn", "hockey", "nhl", "Hurricanes", "NHL"),
    "blue jackets": ("espn", "hockey", "nhl", "Blue Jackets", "NHL"),
    "devils": ("espn", "hockey", "nhl", "Devils", "NHL"),
    "islanders": ("espn", "hockey", "nhl", "Islanders", "NHL"),
    "isles": ("espn", "hockey", "nhl", "Islanders", "NHL"),
    "nhl rangers": ("espn", "hockey", "nhl", "Rangers", "NHL"),
    "flyers": ("espn", "hockey", "nhl", "Flyers", "NHL"),
    "penguins": ("espn", "hockey", "nhl", "Penguins", "NHL"),
    "pens": ("espn", "hockey", "nhl", "Penguins", "NHL"),
    "capitals": ("espn", "hockey", "nhl", "Capitals", "NHL"),
    "caps": ("espn", "hockey", "nhl", "Capitals", "NHL"),
    "blackhawks": ("espn", "hockey", "nhl", "Blackhawks", "NHL"),
    "hawks": ("espn", "hockey", "nhl", "Blackhawks", "NHL"),
    "avalanche": ("espn", "hockey", "nhl", "Avalanche", "NHL"),
    "avs": ("espn", "hockey", "nhl", "Avalanche", "NHL"),
    "stars": ("espn", "hockey", "nhl", "Stars", "NHL"),
    "wild": ("espn", "hockey", "nhl", "Wild", "NHL"),
    "predators": ("espn", "hockey", "nhl", "Predators", "NHL"),
    "preds": ("espn", "hockey", "nhl", "Predators", "NHL"),
    "nhl blues": ("espn", "hockey", "nhl", "Blues", "NHL"),
    "utah": ("espn", "hockey", "nhl", "Utah", "NHL"),
    "nhl jets": ("espn", "hockey", "nhl", "Jets", "NHL"),
    "ducks": ("espn", "hockey", "nhl", "Ducks", "NHL"),
    "flames": ("espn", "hockey", "nhl", "Flames", "NHL"),
    "oilers": ("espn", "hockey", "nhl", "Oilers", "NHL"),
    "nhl kings": ("espn", "hockey", "nhl", "Kings", "NHL"),
    "sharks": ("espn", "hockey", "nhl", "Sharks", "NHL"),
    "kraken": ("espn", "hockey", "nhl", "Kraken", "NHL"),
    "canucks": ("espn", "hockey", "nhl", "Canucks", "NHL"),
    "nucks": ("espn", "hockey", "nhl", "Canucks", "NHL"),
    "golden knights": ("espn", "hockey", "nhl", "Golden Knights", "NHL"),
    "vgas": ("espn", "hockey", "nhl", "Golden Knights", "NHL"),
    # === HOCKEY (PWHL) ===
    "charge": ("espn", "hockey", "pwhl", "Charge", "PWHL"),
    "ottawa charge": ("espn", "hockey", "pwhl", "Charge", "PWHL"),
    "sceptres": ("espn", "hockey", "pwhl", "Sceptres", "PWHL"),
    "toronto sceptres": ("espn", "hockey", "pwhl", "Sceptres", "PWHL"),
    "victoire": ("espn", "hockey", "pwhl", "Victoire", "PWHL"),
    "montreal victoire": ("espn", "hockey", "pwhl", "Victoire", "PWHL"),
    "fleet": ("espn", "hockey", "pwhl", "Fleet", "PWHL"),
    "boston fleet": ("espn", "hockey", "pwhl", "Fleet", "PWHL"),
    "frost": ("espn", "hockey", "pwhl", "Frost", "PWHL"),
    "minnesota frost": ("espn", "hockey", "pwhl", "Frost", "PWHL"),
    "sirens": ("espn", "hockey", "pwhl", "Sirens", "PWHL"),
    "new york sirens": ("espn", "hockey", "pwhl", "Sirens", "PWHL"),
    # === BASKETBALL (NBA) ===
    "raps": ("espn", "basketball", "nba", "Raptors", "NBA"),
    "raptors": ("espn", "basketball", "nba", "Raptors", "NBA"),
    "toronto raptors": ("espn", "basketball", "nba", "Raptors", "NBA"),
    "raptros": ("espn", "basketball", "nba", "Raptors", "NBA"),
    "celtics": ("espn", "basketball", "nba", "Celtics", "NBA"),
    "nets": ("espn", "basketball", "nba", "Nets", "NBA"),
    "knicks": ("espn", "basketball", "nba", "Knicks", "NBA"),
    "76ers": ("espn", "basketball", "nba", "76ers", "NBA"),
    "sixers": ("espn", "basketball", "nba", "76ers", "NBA"),
    "bulls": ("espn", "basketball", "nba", "Bulls", "NBA"),
    "cavaliers": ("espn", "basketball", "nba", "Cavaliers", "NBA"),
    "cavs": ("espn", "basketball", "nba", "Cavaliers", "NBA"),
    "pistons": ("espn", "basketball", "nba", "Pistons", "NBA"),
    "pacers": ("espn", "basketball", "nba", "Pacers", "NBA"),
    "bucks": ("espn", "basketball", "nba", "Bucks", "NBA"),
    "hawks nba": ("espn", "basketball", "nba", "Hawks", "NBA"),
    "hornets": ("espn", "basketball", "nba", "Hornets", "NBA"),
    "heat": ("espn", "basketball", "nba", "Heat", "NBA"),
    "magic": ("espn", "basketball", "nba", "Magic", "NBA"),
    "wizards": ("espn", "basketball", "nba", "Wizards", "NBA"),
    "nuggets": ("espn", "basketball", "nba", "Nuggets", "NBA"),
    "timberwolves": ("espn", "basketball", "nba", "Timberwolves", "NBA"),
    "wolves": ("espn", "basketball", "nba", "Timberwolves", "NBA"),
    "thunder": ("espn", "basketball", "nba", "Thunder", "NBA"),
    "okc": ("espn", "basketball", "nba", "Thunder", "NBA"),
    "trail blazers": ("espn", "basketball", "nba", "Trail Blazers", "NBA"),
    "blazers": ("espn", "basketball", "nba", "Trail Blazers", "NBA"),
    "jazz": ("espn", "basketball", "nba", "Jazz", "NBA"),
    "warriors": ("espn", "basketball", "nba", "Warriors", "NBA"),
    "dubs": ("espn", "basketball", "nba", "Warriors", "NBA"),
    "clippers": ("espn", "basketball", "nba", "Clippers", "NBA"),
    "lakers": ("espn", "basketball", "nba", "Lakers", "NBA"),
    "suns": ("espn", "basketball", "nba", "Suns", "NBA"),
    "nba kings": ("espn", "basketball", "nba", "Kings", "NBA"),
    "mavericks": ("espn", "basketball", "nba", "Mavericks", "NBA"),
    "mavs": ("espn", "basketball", "nba", "Mavericks", "NBA"),
    "rockets": ("espn", "basketball", "nba", "Rockets", "NBA"),
    "grizzlies": ("espn", "basketball", "nba", "Grizzlies", "NBA"),
    "pelicans": ("espn", "basketball", "nba", "Pelicans", "NBA"),
    "spurs": ("espn", "basketball", "nba", "Spurs", "NBA"),
    # === BASKETBALL (WNBA) ===
    "aces": ("espn", "basketball", "wnba", "Aces", "WNBA"),
    "dream": ("espn", "basketball", "wnba", "Dream", "WNBA"),
    "sky": ("espn", "basketball", "wnba", "Sky", "WNBA"),
    "sun": ("espn", "basketball", "wnba", "Sun", "WNBA"),
    "fever": ("espn", "basketball", "wnba", "Fever", "WNBA"),
    "liberty": ("espn", "basketball", "wnba", "Liberty", "WNBA"),
    "sparks": ("espn", "basketball", "wnba", "Sparks", "WNBA"),
    "lynx": ("espn", "basketball", "wnba", "Lynx", "WNBA"),
    "mercury": ("espn", "basketball", "wnba", "Mercury", "WNBA"),
    "storm": ("espn", "basketball", "wnba", "Storm", "WNBA"),
    "wings": ("espn", "basketball", "wnba", "Wings", "WNBA"),
    "mystics": ("espn", "basketball", "wnba", "Mystics", "WNBA"),
    "tempo": ("espn", "basketball", "wnba", "Tempo", "WNBA"),
    "toronto tempo": ("espn", "basketball", "wnba", "Tempo", "WNBA"),
    "valkyries": ("espn", "basketball", "wnba", "Valkyries", "WNBA"),
    "golden state valkyries": ("espn", "basketball", "wnba", "Valkyries", "WNBA"),
    "fire": ("espn", "basketball", "wnba", "Fire", "WNBA"),
    "portland fire": ("espn", "basketball", "wnba", "Fire", "WNBA"),
    # === FOOTBALL (NFL) ===
    "bills": ("espn", "football", "nfl", "Bills", "NFL"),
    "buffalo": ("espn", "football", "nfl", "Bills", "NFL"),
    "dolphins": ("espn", "football", "nfl", "Dolphins", "NFL"),
    "patriots": ("espn", "football", "nfl", "Patriots", "NFL"),
    "pats": ("espn", "football", "nfl", "Patriots", "NFL"),
    "ny jets": ("espn", "football", "nfl", "Jets", "NFL"),
    "nfl jets": ("espn", "football", "nfl", "Jets", "NFL"),
    "ravens": ("espn", "football", "nfl", "Ravens", "NFL"),
    "bengals": ("espn", "football", "nfl", "Bengals", "NFL"),
    "browns": ("espn", "football", "nfl", "Browns", "NFL"),
    "steelers": ("espn", "football", "nfl", "Steelers", "NFL"),
    "texans": ("espn", "football", "nfl", "Texans", "NFL"),
    "colts": ("espn", "football", "nfl", "Colts", "NFL"),
    "jaguars": ("espn", "football", "nfl", "Jaguars", "NFL"),
    "jags": ("espn", "football", "nfl", "Jaguars", "NFL"),
    "titans nfl": ("espn", "football", "nfl", "Titans", "NFL"),
    "broncos": ("espn", "football", "nfl", "Broncos", "NFL"),
    "chiefs": ("espn", "football", "nfl", "Chiefs", "NFL"),
    "raiders": ("espn", "football", "nfl", "Raiders", "NFL"),
    "chargers": ("espn", "football", "nfl", "Chargers", "NFL"),
    "cowboys": ("espn", "football", "nfl", "Cowboys", "NFL"),
    "ny giants": ("espn", "football", "nfl", "Giants", "NFL"),
    "nfl giants": ("espn", "football", "nfl", "Giants", "NFL"),
    "eagles": ("espn", "football", "nfl", "Eagles", "NFL"),
    "commanders": ("espn", "football", "nfl", "Commanders", "NFL"),
    "bears": ("espn", "football", "nfl", "Bears", "NFL"),
    "detroit lions": ("espn", "football", "nfl", "Lions", "NFL"),
    "packers": ("espn", "football", "nfl", "Packers", "NFL"),
    "vikings": ("espn", "football", "nfl", "Vikings", "NFL"),
    "falcons": ("espn", "football", "nfl", "Falcons", "NFL"),
    "nfl panthers": ("espn", "football", "nfl", "Panthers", "NFL"),
    "saints": ("espn", "football", "nfl", "Saints", "NFL"),
    "buccaneers": ("espn", "football", "nfl", "Buccaneers", "NFL"),
    "bucs": ("espn", "football", "nfl", "Buccaneers", "NFL"),
    "nfl cardinals": ("espn", "football", "nfl", "Cardinals", "NFL"),
    "rams": ("espn", "football", "nfl", "Rams", "NFL"),
    "49ers": ("espn", "football", "nfl", "49ers", "NFL"),
    "niners": ("espn", "football", "nfl", "49ers", "NFL"),
    "seahawks": ("espn", "football", "nfl", "Seahawks", "NFL"),
    # === SOCCER (MLS) ===
    "tfc": ("espn", "soccer", "usa.1", "Toronto FC", "MLS"),
    "toronto fc": ("espn", "soccer", "usa.1", "Toronto FC", "MLS"),
    "cf montreal": ("espn", "soccer", "usa.1", "CF Montréal", "MLS"),
    "montreal impact": ("espn", "soccer", "usa.1", "CF Montréal", "MLS"),
    "whitecaps": ("espn", "soccer", "usa.1", "Whitecaps", "MLS"),
    "vancouver whitecaps": ("espn", "soccer", "usa.1", "Whitecaps", "MLS"),
    "inter miami": ("espn", "soccer", "usa.1", "Inter Miami", "MLS"),
    "miami fc": ("espn", "soccer", "usa.1", "Inter Miami", "MLS"),
    "lafc": ("espn", "soccer", "usa.1", "LAFC", "MLS"),
    "la galaxy": ("espn", "soccer", "usa.1", "LA Galaxy", "MLS"),
    "sounders": ("espn", "soccer", "usa.1", "Sounders", "MLS"),
    "seattle sounders": ("espn", "soccer", "usa.1", "Sounders", "MLS"),
    "timbers": ("espn", "soccer", "usa.1", "Timbers", "MLS"),
    "portland timbers": ("espn", "soccer", "usa.1", "Timbers", "MLS"),
    "crew": ("espn", "soccer", "usa.1", "Crew", "MLS"),
    "columbus crew": ("espn", "soccer", "usa.1", "Crew", "MLS"),
    # === SOCCER (EPL) ===
    "arsenal": ("espn", "soccer", "eng.1", "Arsenal", "EPL"),
    "aston villa": ("espn", "soccer", "eng.1", "Aston Villa", "EPL"),
    "villa": ("espn", "soccer", "eng.1", "Aston Villa", "EPL"),
    "bournemouth": ("espn", "soccer", "eng.1", "Bournemouth", "EPL"),
    "brentford": ("espn", "soccer", "eng.1", "Brentford", "EPL"),
    "brighton": ("espn", "soccer", "eng.1", "Brighton", "EPL"),
    "chelsea": ("espn", "soccer", "eng.1", "Chelsea", "EPL"),
    "crystal palace": ("espn", "soccer", "eng.1", "Crystal Palace", "EPL"),
    "palace": ("espn", "soccer", "eng.1", "Crystal Palace", "EPL"),
    "everton": ("espn", "soccer", "eng.1", "Everton", "EPL"),
    "fulham": ("espn", "soccer", "eng.1", "Fulham", "EPL"),
    "liverpool": ("espn", "soccer", "eng.1", "Liverpool", "EPL"),
    "man city": ("espn", "soccer", "eng.1", "Manchester City", "EPL"),
    "manchester city": ("espn", "soccer", "eng.1", "Manchester City", "EPL"),
    "man utd": ("espn", "soccer", "eng.1", "Manchester United", "EPL"),
    "manchester united": ("espn", "soccer", "eng.1", "Manchester United", "EPL"),
    "united": ("espn", "soccer", "eng.1", "Manchester United", "EPL"),
    "newcastle": ("espn", "soccer", "eng.1", "Newcastle", "EPL"),
    "forest": ("espn", "soccer", "eng.1", "Nottingham Forest", "EPL"),
    "nottm forest": ("espn", "soccer", "eng.1", "Nottingham Forest", "EPL"),
    "spurs epl": ("espn", "soccer", "eng.1", "Tottenham", "EPL"),
    "tottenham": ("espn", "soccer", "eng.1", "Tottenham", "EPL"),
    "west ham": ("espn", "soccer", "eng.1", "West Ham", "EPL"),
    "wolves": ("espn", "soccer", "eng.1", "Wolverhampton", "EPL"),
    "wolverhampton": ("espn", "soccer", "eng.1", "Wolverhampton", "EPL"),
    "leicest city": ("espn", "soccer", "eng.1", "Leicester City", "EPL"),
    "leicest": ("espn", "soccer", "eng.1", "Leicester City", "EPL"),
    "leicester city": ("espn", "soccer", "eng.1", "Leicester City", "EPL"),
    # === SOCCER (La Liga) ===
    "real madrid": ("espn", "soccer", "esp.1", "Real Madrid", "La Liga"),
    "madrid": ("espn", "soccer", "esp.1", "Real Madrid", "La Liga"),
    "barcelona": ("espn", "soccer", "esp.1", "Barcelona", "La Liga"),
    "barca": ("espn", "soccer", "esp.1", "Barcelona", "La Liga"),
    "atletico madrid": ("espn", "soccer", "esp.1", "Atlético Madrid", "La Liga"),
    "sevilla": ("espn", "soccer", "esp.1", "Sevilla", "La Liga"),
    "valencia": ("espn", "soccer", "esp.1", "Valencia", "La Liga"),
    "villarreal": ("espn", "soccer", "esp.1", "Villarreal", "La Liga"),
    "real sociedad": ("espn", "soccer", "esp.1", "Real Sociedad", "La Liga"),
    # === SOCCER (Bundesliga) ===
    "bayern": ("espn", "soccer", "ger.1", "Bayern Munich", "Bundesliga"),
    "bayern munich": ("espn", "soccer", "ger.1", "Bayern Munich", "Bundesliga"),
    "dortmund": ("espn", "soccer", "ger.1", "Borussia Dortmund", "Bundesliga"),
    "bvb": ("espn", "soccer", "ger.1", "Borussia Dortmund", "Bundesliga"),
    "leverkusen": ("espn", "soccer", "ger.1", "Bayer Leverkusen", "Bundesliga"),
    "bayer leverkusen": ("espn", "soccer", "ger.1", "Bayer Leverkusen", "Bundesliga"),
    "leipzig": ("espn", "soccer", "ger.1", "RB Leipzig", "Bundesliga"),
    "rb leipzig": ("espn", "soccer", "ger.1", "RB Leipzig", "Bundesliga"),
    "stuttgart": ("espn", "soccer", "ger.1", "VfB Stuttgart", "Bundesliga"),
    "eintracht": ("espn", "soccer", "eng.1", "Eintracht Frankfurt", "Bundesliga"),
    # =========================================================================
    # === CFL (Dynamic JSON Tracker)                                        ===
    # =========================================================================
    "redblacks": ("ha_cfl", "cfl", "Redblacks", "CFL"),
    "ottawa redblacks": ("ha_cfl", "cfl", "Redblacks", "CFL"),
    "argos": ("ha_cfl", "cfl", "Argonauts", "CFL"),
    "toronto argonauts": ("ha_cfl", "cfl", "Argonauts", "CFL"),
    "alouettes": ("ha_cfl", "cfl", "Alouettes", "CFL"),
    "als": ("ha_cfl", "cfl", "Alouettes", "CFL"),
    "tiger-cats": ("ha_cfl", "cfl", "Tiger-Cats", "CFL"),
    "ticats": ("ha_cfl", "cfl", "Tiger-Cats", "CFL"),
    "tiger cats": ("ha_cfl", "cfl", "Tiger-Cats", "CFL"),
    "blue bombers": ("ha_cfl", "cfl", "Blue Bombers", "CFL"),
    "bombers": ("ha_cfl", "cfl", "Blue Bombers", "CFL"),
    "roughriders": ("ha_cfl", "cfl", "Roughriders", "CFL"),
    "riders": ("ha_cfl", "cfl", "Roughriders", "CFL"),
    "elks": ("ha_cfl", "cfl", "Elks", "CFL"),
    "stampeders": ("ha_cfl", "cfl", "Stampeders", "CFL"),
    "stamps": ("ha_cfl", "cfl", "Stampeders", "CFL"),
    "bc lions": ("ha_cfl", "cfl", "BC Lions", "CFL"),
    # =========================================================================
    # === DISABLED MINOR LEAGUES                                            ===
    # =========================================================================
    "67s": ("disabled", "Ottawa 67s", "OHL"),
    "ottawa 67s": ("disabled", "Ottawa 67s", "OHL"),
    "generals": ("disabled", "Oshawa Generals", "OHL"),
    "oshawa generals": ("disabled", "Oshawa Generals", "OHL"),
    "petes": ("disabled", "Peterborough Petes", "OHL"),
    "peterborough petes": ("disabled", "Peterborough Petes", "OHL"),
    "knights": ("disabled", "London Knights", "OHL"),
    "london knights": ("disabled", "London Knights", "OHL"),
    "rangers ohl": ("disabled", "Kitchener Rangers", "OHL"),
    "kitchener rangers": ("disabled", "Kitchener Rangers", "OHL"),
    "blackjacks": ("disabled", "Ottawa BlackJacks", "CEBL"),
    "ottawa blackjacks": ("disabled", "Ottawa BlackJacks", "CEBL"),
    "atletico ottawa": ("disabled", "Atletico Ottawa", "CPL"),
    "black bears": ("disabled", "Ottawa Black Bears", "NLL"),
    "titans": ("disabled", "Ottawa Titans", "Frontier"),
}

OTTAWA_TEAMS = [
    "ottawa senators",
    "ottawa charge",
    "ottawa redblacks",
    "atletico ottawa",
    "ottawa blackjacks",
    "ottawa 67s",
    "ottawa rapid",
    "ottawa black bears",
    "ottawa titans",
]

TORONTO_TEAMS = [
    "toronto maple leafs",
    "toronto sceptres",
    "toronto raptors",
    "toronto tempo",
    "toronto blue jays",
    "toronto argonauts",
    "toronto fc",
]


def get_local_date(iso_str: str) -> str:
    """Offsets UTC strings by -4 hours to correctly group night games into local date."""
    if not iso_str:
        return "2099-12-31"
    try:
        clean_date = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_date) - timedelta(hours=4)
        return dt.strftime("%Y-%m-%d")
    except:
        return iso_str[:10]


async def fetch_ha_cfl(
    search_team: str,
    league_label: str,
    scope: str = "default",
    return_raw: bool = False,
) -> str:
    """Dynamically parses the live CFL scoreboard JSON payload."""
    url = "https://cflscoreboard.cfl.ca/json/scoreboard/rounds.json"

    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
        )
        resp = await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
        raw_data = resp.read()

        # Safely decompress if the server returns a gzip payload
        if resp.info().get("Content-Encoding") == "gzip":
            raw_data = gzip.decompress(raw_data)

        schedule_data = json.loads(raw_data.decode("utf-8"))
    except Exception as e:
        if return_raw:
            return ""
        return f"[{league_label}] Fetch failed: {e}"

    now = datetime.now()
    target_m = now.month
    target_d = now.day
    tom = now + timedelta(days=1)

    events: list[CFLEvent] = []
    for week in schedule_data:
        for game in week.get("tournaments", []):
            date_str = game.get("date")
            if not date_str:
                continue

            # Converts ISO 8601 UTC to Local EDT (-4 hours)
            dt_utc = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
            dt_local = dt_utc - timedelta(hours=4)

            home = game.get("homeSquad", {})
            away = game.get("awaySquad", {})

            api_status = game.get("status", "scheduled").lower()

            # Failsafe: Combats API lag by forcing a game to "playing" if it's past kickoff
            # and the CFL hasn't updated the payload to 'complete' yet.
            if api_status in ["playing", "in progress", "in-progress"]:
                status = "playing"
            elif api_status in ["complete", "final"]:
                status = "complete"
            else:
                if dt_local <= now <= dt_local + timedelta(hours=4):
                    status = "playing"
                else:
                    status = "scheduled"

            events.append(
                {
                    "month": dt_local.month,
                    "day": dt_local.day,
                    "time_str": dt_local.strftime("%I:%M %p").lstrip("0"),
                    "away": away.get("shortName", "???").upper(),
                    "home": home.get("shortName", "???").upper(),
                    "away_name": away.get("name", "").lower(),
                    "home_name": home.get("name", "").lower(),
                    "away_score": away.get("score", 0),
                    "home_score": home.get("score", 0),
                    "status": status,
                    "dt": dt_local,
                }
            )

    if search_team:
        s_name = search_team.lower()
        events = [
            e
            for e in events
            if s_name in e["away_name"]
            or s_name in e["home_name"]
            or s_name == e["away"].lower()
            or s_name == e["home"].lower()
        ]

    matches: list[CFLEvent] = []
    actual_scope = scope

    if scope in ["default", "today"]:
        matches = [e for e in events if e["month"] == target_m and e["day"] == target_d]
        if not matches and search_team and scope == "default":
            future = [e for e in events if e["dt"] > now]
            if future:
                future.sort(key=lambda x: x["dt"])
                matches = [future[0]]
                actual_scope = "next"
    elif scope == "live":
        matches = [e for e in events if e["status"] == "playing"]
    elif scope == "tomorrow":
        matches = [e for e in events if e["month"] == tom.month and e["day"] == tom.day]
    elif scope == "next":
        future = [e for e in events if e["dt"] > now]
        if future:
            future.sort(key=lambda x: x["dt"])
            if search_team:
                matches = [future[0]]
            else:
                first_dt = future[0]["dt"]
                matches = [
                    e
                    for e in future
                    if e["month"] == first_dt.month and e["day"] == first_dt.day
                ]

    if not matches:
        if return_raw:
            return ""
        display_scope = "today" if scope == "default" and not search_team else scope
        subj = search_team.title() if search_team else league_label
        return f"{'['+league_label+']' if search_team else league_label+':'} No games {display_scope}{' for '+subj if search_team else ''}."

    pairs = []
    for e in matches:
        if e["status"] == "complete":
            status_display = "F"
        elif e["status"] == "playing":
            status_display = "Live"
        else:
            if actual_scope == "next" or (
                e["month"] != target_m or e["day"] != target_d
            ):
                status_display = f"{e['month']}/{e['day']} {e['time_str']}"
            else:
                status_display = e["time_str"]

        if e["status"] in ["playing", "complete"]:
            score_str = f" {e['away_score']} @ {e['home']} {e['home_score']}"
            game_str = f"{e['away']}{score_str}({status_display})"
        else:
            game_str = f"{e['away']} @ {e['home']}({status_display})"

        prefix = "Next: " if actual_scope == "next" and search_team else ""
        pairs.append(f"{prefix}{game_str}")

    if search_team:
        res = f"[{league_label}] " + " | ".join(pairs)
    else:
        prefix_scope = (
            f"{league_label} NEXT: "
            if actual_scope == "next"
            else f"{league_label} {actual_scope.upper()}: "
        )
        res = prefix_scope + ", ".join(pairs)

    if return_raw:
        return res
    return res


def format_event(event: dict, team_query: str = "", scope: str = "") -> str:
    try:
        comps = event.get("competitions", [])
        if not comps:
            return ""
        comp = comps[0]

        state = comp.get("status", {}).get("type", {}).get("state", "")
        detail = comp.get("status", {}).get("type", {}).get("shortDetail", "")

        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            return ""

        home = next(
            (c for c in competitors if c.get("homeAway") == "home"), competitors[0]
        )
        away = next(
            (c for c in competitors if c.get("homeAway") == "away"), competitors[1]
        )

        h_abbr = (
            home.get("team", {})
            .get("abbreviation", home.get("team", {}).get("displayName", "???")[:3])
            .upper()
            .strip()
        )
        a_abbr = (
            away.get("team", {})
            .get("abbreviation", away.get("team", {}).get("displayName", "???")[:3])
            .upper()
            .strip()
        )

        h_score = home.get("score", "0")
        a_score = away.get("score", "0")

        if state == "in":
            return f"{a_abbr} {a_score} @ {h_abbr} {h_score}"
        elif state == "post":
            if "postponed" in detail.lower() or "canceled" in detail.lower():
                return f"{a_abbr} @ {h_abbr}({detail})"
            return f"{a_abbr} {a_score} @ {h_abbr} {h_score}(F)"
        else:
            event_date = event.get("date", "")
            if event_date:
                try:
                    clean_date = event_date.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(clean_date) - timedelta(hours=4)

                    time_fmt = dt.strftime("%I:%M %p").lstrip("0")

                    if "TBD" in detail.upper() or dt.strftime("%H:%M") in [
                        "00:00",
                        "04:00",
                    ]:
                        time_str = "TBD"
                    else:
                        time_str = time_fmt

                    if scope in ["today", "tomorrow"]:
                        t = time_str
                    else:
                        t = f"{dt.month}/{dt.day} {time_str}".strip()
                except:
                    t = "TBD"
            else:
                t = "TBD"

            prefix = "Next: " if scope == "next" and team_query else ""
            return f"{prefix}{a_abbr} @ {h_abbr}({t})"
    except Exception:
        return ""


def fetch_f1_slate(scope: str = "default") -> str:
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read()
            if response.info().get("Content-Encoding") == "gzip":
                raw_data = gzip.decompress(raw_data)
            data = json.loads(raw_data.decode("utf-8"))

        events = data.get("events", [])
        if not events:
            return "F1: No events found."
        events.sort(key=lambda x: x.get("date", ""))

        if scope == "next":
            for e in events:
                if (
                    e.get("competitions", [{}])[0]
                    .get("status", {})
                    .get("type", {})
                    .get("state", "")
                    == "pre"
                ):
                    name = e.get("shortName", e.get("name", "Race"))
                    dt = datetime.fromisoformat(
                        e.get("date", "").replace("Z", "+00:00")
                    )
                    return f"F1 NEXT: {name} ({dt.month}/{dt.day})"
            return "F1: No upcoming races scheduled."

        live_events = [
            e
            for e in events
            if e.get("competitions", [{}])[0]
            .get("status", {})
            .get("type", {})
            .get("state", "")
            == "in"
        ]
        if live_events:
            e = live_events[0]
            name = e.get("shortName", e.get("name", "Race"))
            comps = e.get("competitions", [{}])[0].get("competitors", [])
            top_drivers = [
                c.get("athlete", {}).get("shortName", "Driver") for c in comps[:3]
            ]
            return f"F1 LIVE: {name} - Top 3: " + ", ".join(top_drivers)

        for e in events:
            if (
                e.get("competitions", [{}])[0]
                .get("status", {})
                .get("type", {})
                .get("state", "")
                == "pre"
            ):
                name = e.get("shortName", e.get("name", "Race"))
                dt = datetime.fromisoformat(e.get("date", "").replace("Z", "+00:00"))
                return f"F1 NEXT: {name} ({dt.month}/{dt.day})"
        return "F1: No live or upcoming races."
    except Exception as e:
        return f"Fetch failed: {e}"


def fetch_espn_league_slate(
    sport: str, league: str, display_name: str, scope: str = "default"
) -> str:
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?limit=200"
    now = datetime.now()
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read()
            if response.info().get("Content-Encoding") == "gzip":
                raw_data = gzip.decompress(raw_data)
            data = json.loads(raw_data.decode("utf-8"))

        events = data.get("events", [])

        display_scope = "today" if scope == "default" else scope
        if not events:
            return f"{display_name}: No games {display_scope}."

        events.sort(key=lambda x: x.get("date", ""))
        pairs = []
        target_m = now.month
        target_d = now.day
        tom = now + timedelta(days=1)

        if scope == "next":
            pre_events = [
                e
                for e in events
                if e.get("competitions", [{}])[0]
                .get("status", {})
                .get("type", {})
                .get("state", "")
                == "pre"
            ]
            if not pre_events:
                return f"{display_name}: No upcoming games scheduled."

            future_events = []
            for e in pre_events:
                d_str = get_local_date(e.get("date", ""))
                try:
                    dt = datetime.strptime(d_str, "%Y-%m-%d")
                    if dt.month > target_m or (
                        dt.month == target_m and dt.day >= target_d
                    ):
                        future_events.append(e)
                except:
                    pass

            if not future_events:
                return f"{display_name}: No upcoming games scheduled."

            first_date = get_local_date(future_events[0].get("date", ""))
            first_m = datetime.strptime(first_date, "%Y-%m-%d").month
            first_d = datetime.strptime(first_date, "%Y-%m-%d").day

            next_slate = [
                e
                for e in future_events
                if datetime.strptime(
                    get_local_date(e.get("date", "")), "%Y-%m-%d"
                ).month
                == first_m
                and datetime.strptime(get_local_date(e.get("date", "")), "%Y-%m-%d").day
                == first_d
            ]
            for e in next_slate:
                formatted = format_event(e, scope=scope)
                if formatted:
                    pairs.append(formatted)
            return f"{display_name} NEXT: " + ", ".join(pairs)

        for e in events:
            state = (
                e.get("competitions", [{}])[0]
                .get("status", {})
                .get("type", {})
                .get("state", "")
            )
            if scope == "live" and state != "in":
                continue

            d_str = get_local_date(e.get("date", ""))
            try:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
            except:
                continue

            if scope in ["default", "today", "live"] and (
                dt.month != target_m or dt.day != target_d
            ):
                continue
            if scope == "tomorrow" and (dt.month != tom.month or dt.day != tom.day):
                continue

            formatted = format_event(e, scope=scope)
            if formatted:
                pairs.append(formatted)

        if not pairs:
            return f"{display_name}: No {'live ' if scope=='live' else ''}games {display_scope}."
        return f"{display_name} {scope.upper()}: " + ", ".join(pairs)
    except Exception as e:
        return f"Fetch failed: {e}"


def fetch_espn_team(
    sport: str,
    league: str,
    search_name: str,
    league_label: str,
    team_query: str,
    scope: str = "default",
    return_raw=False,
) -> str:
    now = datetime.now()
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?limit=1000"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read()
            if response.info().get("Content-Encoding") == "gzip":
                raw_data = gzip.decompress(raw_data)
            all_raw_events = json.loads(raw_data.decode("utf-8")).get("events", [])
    except:
        all_raw_events = []

    team_events = []
    seen_event_ids = set()
    s_name = search_name.lower().replace("é", "e")

    for e in all_raw_events:
        eid = e.get("id")
        if eid and eid in seen_event_ids:
            continue
        comps = e.get("competitions", [])
        if not comps:
            continue
        competitors = comps[0].get("competitors", [])
        if len(competitors) < 2:
            continue

        c0, c1 = competitors[0].get("team", {}), competitors[1].get("team", {})
        c0_names = [
            c0.get("displayName", "").lower(),
            c0.get("shortDisplayName", "").lower(),
            c0.get("name", "").lower(),
            c0.get("abbreviation", "").lower(),
        ]
        c1_names = [
            c1.get("displayName", "").lower(),
            c1.get("shortDisplayName", "").lower(),
            c1.get("name", "").lower(),
            c1.get("abbreviation", "").lower(),
        ]

        if any(s_name in n for n in c0_names) or any(s_name in n for n in c1_names):
            if eid:
                seen_event_ids.add(eid)
            team_events.append(e)

    if not team_events:
        if return_raw:
            return ""
        display_scope = "today" if scope == "default" else scope
        return (
            f"[{league_label}] No upcoming games scheduled for {search_name.title()}."
        )

    team_events.sort(key=lambda x: x.get("date", ""))

    pre, live, post = [], [], []
    for e in team_events:
        state = (
            e.get("competitions", [{}])[0]
            .get("status", {})
            .get("type", {})
            .get("state", "")
        )
        if state == "pre":
            pre.append(e)
        elif state == "in":
            live.append(e)
        elif state == "post":
            post.append(e)

    if scope == "next":
        if live:
            fmt = format_event(live[0], team_query, scope)
            if fmt:
                return f"[{league_label}] Live Now: " + fmt
        if pre:
            fmt = format_event(pre[0], team_query, scope)
            if fmt:
                return f"[{league_label}] " + fmt
        if return_raw:
            return ""
        return (
            f"[{league_label}] No upcoming games scheduled for {search_name.title()}."
        )

    msg_parts = []
    target_m, target_d = now.month, now.day
    tom = now + timedelta(days=1)

    if scope in ["default", "today", "live"]:
        if live:
            fmt = format_event(live[0], team_query, scope)
            if fmt:
                msg_parts.append(fmt)
        else:
            today_games = []
            for g in post + pre:
                try:
                    dt = datetime.strptime(
                        get_local_date(g.get("date", "")), "%Y-%m-%d"
                    )
                    if dt.month == target_m and dt.day == target_d:
                        today_games.append(g)
                except:
                    pass
            if today_games:
                fmt = format_event(today_games[-1], team_query, scope)
                if fmt:
                    msg_parts.append(fmt)
            elif scope == "default" and pre:
                fmt = format_event(pre[0], team_query, "next")
                if fmt:
                    msg_parts.append(fmt)
    elif scope == "tomorrow":
        tom_games = []
        for g in team_events:
            try:
                dt = datetime.strptime(get_local_date(g.get("date", "")), "%Y-%m-%d")
                if dt.month == tom.month and dt.day == tom.day:
                    tom_games.append(g)
            except:
                pass
        if tom_games:
            fmt = format_event(tom_games[0], team_query, scope)
            if fmt:
                msg_parts.append(fmt)

    if msg_parts:
        return f"[{league_label}] " + " | ".join(msg_parts)

    if return_raw:
        return ""
    display_scope = "today" if scope == "default" else scope
    return f"[{league_label}] No games {display_scope} for {search_name.title()}."


async def fetch_city_slate(city_query: str, scope: str) -> str:
    teams = (
        OTTAWA_TEAMS
        if city_query == "ottawa"
        else TORONTO_TEAMS if city_query == "toronto" else []
    )
    team_scope = "today" if scope == "default" else scope
    results = []

    for team_key in teams:
        lookup = TEAM_MAP.get(team_key)
        if not lookup:
            continue
        try:
            source = lookup[0]
            if source == "espn":
                res = await asyncio.to_thread(
                    fetch_espn_team,
                    lookup[1],
                    lookup[2],
                    lookup[3],
                    lookup[4],
                    team_key,
                    team_scope,
                    True,
                )
            elif source == "ha_cfl":
                res = await fetch_ha_cfl(lookup[2], lookup[3], team_scope, True)
            elif source == "disabled":
                continue
            if res and "No games" not in res and "No upcoming" not in res:
                results.append(res)
        except:
            continue

    if not results:
        display_scope = "today" if scope == "default" else scope
        return (
            f"YOW {display_scope.title()}: No games scheduled."
            if city_query == "ottawa"
            else f"{city_query.title()} Sports: No games {display_scope}."
        )

    display_scope = "today" if scope == "default" else scope
    return (
        f"YOW {display_scope.title()}: "
        if city_query == "ottawa"
        else f"{city_query.title()} Sports: "
    ) + " || ".join(results)


@command("score", help="Get sports scores or live slates")
async def score(ctx: Context) -> str:
    who = ctx.sender_name or "you"
    query = (
        "".join(str(a) for a in ctx.args).strip()
        if hasattr(ctx, "args") and ctx.args
        else ""
    )

    if not query:
        return f"@[{who}] Try !score help for commands. Leagues: {', '.join(VALID_LEAGUES)}"

    parts = query.lower().split()
    if parts[0] == "help":
        return f"@[{who}] !score help: [team] OR [league] [today/tomorrow/next/live]. Leagues: {', '.join(VALID_LEAGUES)}"
    if parts[0] == "live" and len(parts) == 1:
        return f"@[{who}] Use format !score [league] live. Leagues: {', '.join(VALID_LEAGUES)}"

    scope = "default"
    league_or_team = query.lower()
    if parts[-1] in ["today", "tomorrow", "next", "live"]:
        scope = parts[-1]
        league_or_team = " ".join(parts[:-1]).strip()

    if not league_or_team:
        return f"@[{who}] Specify team or league."

    try:
        if league_or_team in AMBIGUOUS_MAP:
            score_text = AMBIGUOUS_MAP[league_or_team]
        elif league_or_team in ["ottawa", "toronto"]:
            score_text = await fetch_city_slate(league_or_team, scope)
        elif league_or_team == "f1":
            score_text = await asyncio.to_thread(fetch_f1_slate, scope)
        elif league_or_team in LEAGUE_MAP:
            lookup = LEAGUE_MAP[league_or_team]
            if lookup[0] == "espn":
                score_text = await asyncio.to_thread(
                    fetch_espn_league_slate, lookup[1], lookup[2], lookup[3], scope
                )
            elif lookup[0] == "ha_cfl":
                score_text = await fetch_ha_cfl("", lookup[2], scope, False)
            else:
                score_text = f"[{lookup[2]}] Integration paused."
        elif league_or_team in TEAM_MAP:
            lookup = TEAM_MAP[league_or_team]
            if lookup[0] == "espn":
                score_text = await asyncio.to_thread(
                    fetch_espn_team,
                    lookup[1],
                    lookup[2],
                    lookup[3],
                    lookup[4],
                    league_or_team,
                    scope,
                )
            elif lookup[0] == "ha_cfl":
                score_text = await fetch_ha_cfl(lookup[2], lookup[3], scope, False)
            else:
                score_text = f"[{lookup[3]}] Integration paused."
        else:
            score_text = f"'{league_or_team}' not mapped. Try !score help"

        msg = f"@[{who}] {score_text}"
    except Exception:
        msg = f"@[{who}] Error fetching scores."

    if len(msg) > 141:
        msg = msg[:138] + "..."
    return msg
