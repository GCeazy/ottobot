"""!score — get live sports scores and game slates from ESPN's universal API."""

import urllib.request
import json
import asyncio
import re
from datetime import datetime, timedelta
from ottobot import Context, command

# League Router Map
LEAGUE_MAP = {
    "mlb": ("baseball", "mlb", "MLB"),
    "nhl": ("hockey", "nhl", "NHL"),
    "nba": ("basketball", "nba", "NBA"),
    "nfl": ("football", "nfl", "NFL"),
    "cfl": ("football", "cfl", "CFL"),
    "wnba": ("basketball", "wnba", "WNBA"),
    "pwhl": ("hockey", "pwhl", "PWHL"),
    "mls": ("soccer", "usa.1", "MLS"),
    "epl": ("soccer", "eng.1", "EPL"),
    "laliga": ("soccer", "esp.1", "La Liga"),
    "bundesliga": ("soccer", "ger.1", "Bundesliga"),
}

VALID_LEAGUES = sorted(list(LEAGUE_MAP.keys()) + ["f1"])

# Ambiguous triggers updated with the new format prompt
AMBIGUOUS_MAP = {
    "giants": "Try using: ny giants or sf giants",
    "jets": "Try using: ny jets or nhl jets",
    "rangers": "Try using: nhl rangers or texas (rangers)",
    "kings": "Try using: nba kings or nhl kings",
    "cardinals": "Try using: nfl cardinals or stl cardinals",
}

# Team Router Map
TEAM_MAP = {
    # === BASEBALL (MLB) ===
    "jays": ("baseball", "mlb", "Blue Jays", "MLB"),
    "blue jays": ("baseball", "mlb", "Blue Jays", "MLB"),
    "toronto": ("baseball", "mlb", "Blue Jays", "MLB"),
    "orioles": ("baseball", "mlb", "Orioles", "MLB"),
    "os": ("baseball", "mlb", "Orioles", "MLB"),
    "baltimore": ("baseball", "mlb", "Orioles", "MLB"),
    "red sox": ("baseball", "mlb", "Red Sox", "MLB"),
    "boston": ("baseball", "mlb", "Red Sox", "MLB"),
    "yankees": ("baseball", "mlb", "Yankees", "MLB"),
    "nyy": ("baseball", "mlb", "Yankees", "MLB"),
    "rays": ("baseball", "mlb", "Rays", "MLB"),
    "tampa bay": ("baseball", "mlb", "Rays", "MLB"),
    "white sox": ("baseball", "mlb", "White Sox", "MLB"),
    "chicago white sox": ("baseball", "mlb", "White Sox", "MLB"),
    "guardians": ("baseball", "mlb", "Guardians", "MLB"),
    "cleveland": ("baseball", "mlb", "Guardians", "MLB"),
    "tigers": ("baseball", "mlb", "Tigers", "MLB"),
    "detroit": ("baseball", "mlb", "Tigers", "MLB"),
    "royals": ("baseball", "mlb", "Royals", "MLB"),
    "kc": ("baseball", "mlb", "Royals", "MLB"),
    "twins": ("baseball", "mlb", "Twins", "MLB"),
    "minnesota": ("baseball", "mlb", "Twins", "MLB"),
    "astros": ("baseball", "mlb", "Astros", "MLB"),
    "houston": ("baseball", "mlb", "Astros", "MLB"),
    "angels": ("baseball", "mlb", "Angels", "MLB"),
    "laa": ("baseball", "mlb", "Angels", "MLB"),
    "athletics": ("baseball", "mlb", "Athletics", "MLB"),
    "as": ("baseball", "mlb", "Athletics", "MLB"),
    "mariners": ("baseball", "mlb", "Mariners", "MLB"),
    "seattle": ("baseball", "mlb", "Mariners", "MLB"),
    "texas": ("baseball", "mlb", "Rangers", "MLB"),
    "texas rangers": ("baseball", "mlb", "Rangers", "MLB"),
    "braves": ("baseball", "mlb", "Braves", "MLB"),
    "atlanta": ("baseball", "mlb", "Braves", "MLB"),
    "marlins": ("baseball", "mlb", "Marlins", "MLB"),
    "miami": ("baseball", "mlb", "Marlins", "MLB"),
    "mets": ("baseball", "mlb", "Mets", "MLB"),
    "nym": ("baseball", "mlb", "Mets", "MLB"),
    "phillies": ("baseball", "mlb", "Phillies", "MLB"),
    "philly": ("baseball", "mlb", "Phillies", "MLB"),
    "nationals": ("baseball", "mlb", "Nationals", "MLB"),
    "nats": ("baseball", "mlb", "Nationals", "MLB"),
    "cubs": ("baseball", "mlb", "Cubs", "MLB"),
    "chicago cubs": ("baseball", "mlb", "Cubs", "MLB"),
    "reds": ("baseball", "mlb", "Reds", "MLB"),
    "cincinnati": ("baseball", "mlb", "Reds", "MLB"),
    "brewers": ("baseball", "mlb", "Brewers", "MLB"),
    "milwaukee": ("baseball", "mlb", "Brewers", "MLB"),
    "pirates": ("baseball", "mlb", "Pirates", "MLB"),
    "pittsburgh": ("baseball", "mlb", "Pirates", "MLB"),
    "stl cardinals": ("baseball", "mlb", "Cardinals", "MLB"),
    "mlb cards": ("baseball", "mlb", "Cardinals", "MLB"),
    "diamondbacks": ("baseball", "mlb", "Diamondbacks", "MLB"),
    "dbacks": ("baseball", "mlb", "Diamondbacks", "MLB"),
    "rockies": ("baseball", "mlb", "Rockies", "MLB"),
    "colorado": ("baseball", "mlb", "Rockies", "MLB"),
    "dodgers": ("baseball", "mlb", "Dodgers", "MLB"),
    "lad": ("baseball", "mlb", "Dodgers", "MLB"),
    "padres": ("baseball", "mlb", "Padres", "MLB"),
    "san diego": ("baseball", "mlb", "Padres", "MLB"),
    "sf giants": ("baseball", "mlb", "Giants", "MLB"),
    "mlb giants": ("baseball", "mlb", "Giants", "MLB"),
    # === HOCKEY (NHL) ===
    "sens": ("hockey", "nhl", "Senators", "NHL"),
    "senators": ("hockey", "nhl", "Senators", "NHL"),
    "ottawa": ("hockey", "nhl", "Senators", "NHL"),
    "leafs": ("hockey", "nhl", "Maple Leafs", "NHL"),
    "maple leafs": ("hockey", "nhl", "Maple Leafs", "NHL"),
    "toronto maple leafs": ("hockey", "nhl", "Maple Leafs", "NHL"),
    "leafs suck": ("hockey", "nhl", "Maple Leafs", "NHL"),
    "habs": ("hockey", "nhl", "Canadiens", "NHL"),
    "canadiens": ("hockey", "nhl", "Canadiens", "NHL"),
    "montreal": ("hockey", "nhl", "Canadiens", "NHL"),
    "bruins": ("hockey", "nhl", "Bruins", "NHL"),
    "sabres": ("hockey", "nhl", "Sabres", "NHL"),
    "red wings": ("hockey", "nhl", "Red Wings", "NHL"),
    "panthers": ("hockey", "nhl", "Panthers", "NHL"),
    "nhl panthers": ("hockey", "nhl", "Panthers", "NHL"),
    "lightning": ("hockey", "nhl", "Lightning", "NHL"),
    "bolts": ("hockey", "nhl", "Lightning", "NHL"),
    "hurricanes": ("hockey", "nhl", "Hurricanes", "NHL"),
    "canes": ("hockey", "nhl", "Hurricanes", "NHL"),
    "blue jackets": ("hockey", "nhl", "Blue Jackets", "NHL"),
    "devils": ("hockey", "nhl", "Devils", "NHL"),
    "islanders": ("hockey", "nhl", "Islanders", "NHL"),
    "isles": ("hockey", "nhl", "Islanders", "NHL"),
    "nhl rangers": ("hockey", "nhl", "Rangers", "NHL"),
    "flyers": ("hockey", "nhl", "Flyers", "NHL"),
    "penguins": ("hockey", "nhl", "Penguins", "NHL"),
    "pens": ("hockey", "nhl", "Penguins", "NHL"),
    "capitals": ("hockey", "nhl", "Capitals", "NHL"),
    "caps": ("hockey", "nhl", "Capitals", "NHL"),
    "blackhawks": ("hockey", "nhl", "Blackhawks", "NHL"),
    "hawks": ("hockey", "nhl", "Blackhawks", "NHL"),
    "avalanche": ("hockey", "nhl", "Avalanche", "NHL"),
    "avs": ("hockey", "nhl", "Avalanche", "NHL"),
    "stars": ("hockey", "nhl", "Stars", "NHL"),
    "wild": ("hockey", "nhl", "Wild", "NHL"),
    "predators": ("hockey", "nhl", "Predators", "NHL"),
    "preds": ("hockey", "nhl", "Predators", "NHL"),
    "nhl blues": ("hockey", "nhl", "Blues", "NHL"),
    "utah": ("hockey", "nhl", "Utah", "NHL"),
    "nhl jets": ("hockey", "nhl", "Jets", "NHL"),
    "ducks": ("hockey", "nhl", "Ducks", "NHL"),
    "flames": ("hockey", "nhl", "Flames", "NHL"),
    "oilers": ("hockey", "nhl", "Oilers", "NHL"),
    "nhl kings": ("hockey", "nhl", "Kings", "NHL"),
    "sharks": ("hockey", "nhl", "Sharks", "NHL"),
    "kraken": ("hockey", "nhl", "Kraken", "NHL"),
    "canucks": ("hockey", "nhl", "Canucks", "NHL"),
    "nucks": ("hockey", "nhl", "Canucks", "NHL"),
    "golden knights": ("hockey", "nhl", "Golden Knights", "NHL"),
    "vgas": ("hockey", "nhl", "Golden Knights", "NHL"),
    # === HOCKEY (PWHL) ===
    "charge": ("hockey", "pwhl", "Charge", "PWHL"),
    "ottawa charge": ("hockey", "pwhl", "Charge", "PWHL"),
    "sceptres": ("hockey", "pwhl", "Sceptres", "PWHL"),
    "toronto sceptres": ("hockey", "pwhl", "Sceptres", "PWHL"),
    "victoire": ("hockey", "pwhl", "Victoire", "PWHL"),
    "montreal victoire": ("hockey", "pwhl", "Victoire", "PWHL"),
    "fleet": ("hockey", "pwhl", "Fleet", "PWHL"),
    "boston fleet": ("hockey", "pwhl", "Fleet", "PWHL"),
    "frost": ("hockey", "pwhl", "Frost", "PWHL"),
    "minnesota frost": ("hockey", "pwhl", "Frost", "PWHL"),
    "sirens": ("hockey", "pwhl", "Sirens", "PWHL"),
    "new york sirens": ("hockey", "pwhl", "Sirens", "PWHL"),
    # === BASKETBALL (NBA) ===
    "raps": ("basketball", "nba", "Raptors", "NBA"),
    "raptors": ("basketball", "nba", "Raptors", "NBA"),
    "toronto raptors": ("basketball", "nba", "Raptors", "NBA"),
    "celtics": ("basketball", "nba", "Celtics", "NBA"),
    "nets": ("basketball", "nba", "Nets", "NBA"),
    "knicks": ("basketball", "nba", "Knicks", "NBA"),
    "76ers": ("basketball", "nba", "76ers", "NBA"),
    "sixers": ("basketball", "nba", "76ers", "NBA"),
    "bulls": ("basketball", "nba", "Bulls", "NBA"),
    "cavaliers": ("basketball", "nba", "Cavaliers", "NBA"),
    "cavs": ("basketball", "nba", "Cavaliers", "NBA"),
    "pistons": ("basketball", "nba", "Pistons", "NBA"),
    "pacers": ("basketball", "nba", "Pacers", "NBA"),
    "bucks": ("basketball", "nba", "Bucks", "NBA"),
    "hawks nba": ("basketball", "nba", "Hawks", "NBA"),
    "hornets": ("basketball", "nba", "Hornets", "NBA"),
    "heat": ("basketball", "nba", "Heat", "NBA"),
    "magic": ("basketball", "nba", "Magic", "NBA"),
    "wizards": ("basketball", "nba", "Wizards", "NBA"),
    "nuggets": ("basketball", "nba", "Nuggets", "NBA"),
    "timberwolves": ("basketball", "nba", "Timberwolves", "NBA"),
    "wolves": ("basketball", "nba", "Timberwolves", "NBA"),
    "thunder": ("basketball", "nba", "Thunder", "NBA"),
    "okc": ("basketball", "nba", "Thunder", "NBA"),
    "trail blazers": ("basketball", "nba", "Trail Blazers", "NBA"),
    "blazers": ("basketball", "nba", "Trail Blazers", "NBA"),
    "jazz": ("basketball", "nba", "Jazz", "NBA"),
    "warriors": ("basketball", "nba", "Warriors", "NBA"),
    "dubs": ("basketball", "nba", "Warriors", "NBA"),
    "clippers": ("basketball", "nba", "Clippers", "NBA"),
    "lakers": ("basketball", "nba", "Lakers", "NBA"),
    "suns": ("basketball", "nba", "Suns", "NBA"),
    "nba kings": ("basketball", "nba", "Kings", "NBA"),
    "mavericks": ("basketball", "nba", "Mavericks", "NBA"),
    "mavs": ("basketball", "nba", "Mavericks", "NBA"),
    "rockets": ("basketball", "nba", "Rockets", "NBA"),
    "grizzlies": ("basketball", "nba", "Grizzlies", "NBA"),
    "pelicans": ("basketball", "nba", "Pelicans", "NBA"),
    "spurs": ("basketball", "nba", "Spurs", "NBA"),
    # === BASKETBALL (WNBA) ===
    "aces": ("basketball", "wnba", "Aces", "WNBA"),
    "dream": ("basketball", "wnba", "Dream", "WNBA"),
    "sky": ("basketball", "wnba", "Sky", "WNBA"),
    "sun": ("basketball", "wnba", "Sun", "WNBA"),
    "fever": ("basketball", "wnba", "Fever", "WNBA"),
    "liberty": ("basketball", "wnba", "Liberty", "WNBA"),
    "sparks": ("basketball", "wnba", "Sparks", "WNBA"),
    "lynx": ("basketball", "wnba", "Lynx", "WNBA"),
    "mercury": ("basketball", "wnba", "Mercury", "WNBA"),
    "storm": ("basketball", "wnba", "Storm", "WNBA"),
    "wings": ("basketball", "wnba", "Wings", "WNBA"),
    "mystics": ("basketball", "wnba", "Mystics", "WNBA"),
    "tempo": ("basketball", "wnba", "Tempo", "WNBA"),
    "toronto tempo": ("basketball", "wnba", "Tempo", "WNBA"),
    "valkyries": ("basketball", "wnba", "Valkyries", "WNBA"),
    "golden state valkyries": ("basketball", "wnba", "Valkyries", "WNBA"),
    "fire": ("basketball", "wnba", "Fire", "WNBA"),
    "portland fire": ("basketball", "wnba", "Fire", "WNBA"),
    # === FOOTBALL (NFL) ===
    "bills": ("football", "nfl", "Bills", "NFL"),
    "buffalo": ("football", "nfl", "Bills", "NFL"),
    "dolphins": ("football", "nfl", "Dolphins", "NFL"),
    "patriots": ("football", "nfl", "Patriots", "NFL"),
    "pats": ("football", "nfl", "Patriots", "NFL"),
    "ny jets": ("football", "nfl", "Jets", "NFL"),
    "nfl jets": ("football", "nfl", "Jets", "NFL"),
    "ravens": ("football", "nfl", "Ravens", "NFL"),
    "bengals": ("football", "nfl", "Bengals", "NFL"),
    "browns": ("football", "nfl", "Browns", "NFL"),
    "steelers": ("football", "nfl", "Steelers", "NFL"),
    "texans": ("football", "nfl", "Texans", "NFL"),
    "colts": ("football", "nfl", "Colts", "NFL"),
    "jaguars": ("football", "nfl", "Jaguars", "NFL"),
    "jags": ("football", "nfl", "Jaguars", "NFL"),
    "titans": ("football", "nfl", "Titans", "NFL"),
    "broncos": ("football", "nfl", "Broncos", "NFL"),
    "chiefs": ("football", "nfl", "Chiefs", "NFL"),
    "raiders": ("football", "nfl", "Raiders", "NFL"),
    "chargers": ("football", "nfl", "Chargers", "NFL"),
    "cowboys": ("football", "nfl", "Cowboys", "NFL"),
    "ny giants": ("football", "nfl", "Giants", "NFL"),
    "nfl giants": ("football", "nfl", "Giants", "NFL"),
    "eagles": ("football", "nfl", "Eagles", "NFL"),
    "commanders": ("football", "nfl", "Commanders", "NFL"),
    "bears": ("football", "nfl", "Bears", "NFL"),
    "lions": ("football", "nfl", "Lions", "NFL"),
    "packers": ("football", "nfl", "Packers", "NFL"),
    "vikings": ("football", "nfl", "Vikings", "NFL"),
    "falcons": ("football", "nfl", "Falcons", "NFL"),
    "nfl panthers": ("football", "nfl", "Panthers", "NFL"),
    "saints": ("football", "nfl", "Saints", "NFL"),
    "buccaneers": ("football", "nfl", "Buccaneers", "NFL"),
    "bucs": ("football", "nfl", "Buccaneers", "NFL"),
    "nfl cardinals": ("football", "nfl", "Cardinals", "NFL"),
    "rams": ("football", "nfl", "Rams", "NFL"),
    "49ers": ("football", "nfl", "49ers", "NFL"),
    "niners": ("football", "nfl", "49ers", "NFL"),
    "seahawks": ("football", "nfl", "Seahawks", "NFL"),
    # === FOOTBALL (CFL) ===
    "redblacks": ("football", "cfl", "RedBlacks", "CFL"),
    "argos": ("football", "cfl", "Argonauts", "CFL"),
    "argonauts": ("football", "cfl", "Argonauts", "CFL"),
    "alouettes": ("football", "cfl", "Alouettes", "CFL"),
    "als": ("football", "cfl", "Alouettes", "CFL"),
    "tiger-cats": ("football", "cfl", "Tiger-Cats", "CFL"),
    "ticats": ("football", "cfl", "Tiger-Cats", "CFL"),
    "blue bombers": ("football", "cfl", "Blue Bombers", "CFL"),
    "bombers": ("football", "cfl", "Blue Bombers", "CFL"),
    "roughriders": ("football", "cfl", "Roughriders", "CFL"),
    "riders": ("football", "cfl", "Roughriders", "CFL"),
    "elks": ("football", "cfl", "Elks", "CFL"),
    "stampeders": ("football", "cfl", "Stampeders", "CFL"),
    "stamps": ("football", "cfl", "Stampeders", "CFL"),
    "bc lions": ("football", "cfl", "Lions", "CFL"),
    # === SOCCER (MLS) ===
    "tfc": ("soccer", "usa.1", "Toronto FC", "MLS"),
    "toronto fc": ("soccer", "usa.1", "Toronto FC", "MLS"),
    "cf montreal": ("soccer", "usa.1", "CF Montréal", "MLS"),
    "montreal impact": ("soccer", "usa.1", "CF Montréal", "MLS"),
    "whitecaps": ("soccer", "usa.1", "Whitecaps", "MLS"),
    "vancouver whitecaps": ("soccer", "usa.1", "Whitecaps", "MLS"),
    "inter miami": ("soccer", "usa.1", "Inter Miami", "MLS"),
    "miami fc": ("soccer", "usa.1", "Inter Miami", "MLS"),
    "lafc": ("soccer", "usa.1", "LAFC", "MLS"),
    "la galaxy": ("soccer", "usa.1", "LA Galaxy", "MLS"),
    "sounders": ("soccer", "usa.1", "Sounders", "MLS"),
    "seattle sounders": ("soccer", "usa.1", "Sounders", "MLS"),
    "timbers": ("soccer", "usa.1", "Timbers", "MLS"),
    "portland timbers": ("soccer", "usa.1", "Timbers", "MLS"),
    "crew": ("soccer", "usa.1", "Crew", "MLS"),
    "columbus crew": ("soccer", "usa.1", "Crew", "MLS"),
    # === SOCCER (EPL) ===
    "arsenal": ("soccer", "eng.1", "Arsenal", "EPL"),
    "aston villa": ("soccer", "eng.1", "Aston Villa", "EPL"),
    "villa": ("soccer", "eng.1", "Aston Villa", "EPL"),
    "bournemouth": ("soccer", "eng.1", "Bournemouth", "EPL"),
    "brentford": ("soccer", "eng.1", "Brentford", "EPL"),
    "brighton": ("soccer", "eng.1", "Brighton", "EPL"),
    "chelsea": ("soccer", "eng.1", "Chelsea", "EPL"),
    "crystal palace": ("soccer", "eng.1", "Crystal Palace", "EPL"),
    "palace": ("soccer", "eng.1", "Crystal Palace", "EPL"),
    "everton": ("soccer", "eng.1", "Everton", "EPL"),
    "fulham": ("soccer", "eng.1", "Fulham", "EPL"),
    "liverpool": ("soccer", "eng.1", "Liverpool", "EPL"),
    "man city": ("soccer", "eng.1", "Manchester City", "EPL"),
    "manchester city": ("soccer", "eng.1", "Manchester City", "EPL"),
    "man utd": ("soccer", "eng.1", "Manchester United", "EPL"),
    "manchester united": ("soccer", "eng.1", "Manchester United", "EPL"),
    "united": ("soccer", "eng.1", "Manchester United", "EPL"),
    "newcastle": ("soccer", "eng.1", "Newcastle", "EPL"),
    "forest": ("soccer", "eng.1", "Nottingham Forest", "EPL"),
    "nottm forest": ("soccer", "eng.1", "Nottingham Forest", "EPL"),
    "spurs epl": ("soccer", "eng.1", "Tottenham", "EPL"),
    "tottenham": ("soccer", "eng.1", "Tottenham", "EPL"),
    "west ham": ("soccer", "eng.1", "West Ham", "EPL"),
    "wolves": ("soccer", "eng.1", "Wolverhampton", "EPL"),
    "wolverhampton": ("soccer", "eng.1", "Wolverhampton", "EPL"),
    # === SOCCER (EFL) ===
    "leeds": ("soccer", "eng.2", "Leeds", "EFL"),
    "leeds united": ("soccer", "eng.2", "Leeds", "EFL"),
    "sunderland": ("soccer", "eng.2", "Sunderland", "EFL"),
    "sheffield united": ("soccer", "eng.2", "Sheffield United", "EFL"),
    "burnley": ("soccer", "eng.2", "Burnley", "EFL"),
    "middlesbrough": ("soccer", "eng.2", "Middlesbrough", "EFL"),
    "wrexham": ("soccer", "eng.3", "Wrexham", "EFL"),
    "birmingham": ("soccer", "eng.3", "Birmingham City", "EFL"),
    "birmingham city": ("soccer", "eng.3", "Birmingham City", "EFL"),
    "bolton": ("soccer", "eng.3", "Bolton", "EFL"),
    "leicester": ("soccer", "eng.3", "Leicester", "EFL"),
    "leicester city": ("soccer", "eng.3", "Leicester", "EFL"),
    "blue foxes": ("soccer", "eng.3", "Leicester", "EFL"),
    # === SOCCER (La Liga) ===
    "real madrid": ("soccer", "esp.1", "Real Madrid", "La Liga"),
    "madrid": ("soccer", "esp.1", "Real Madrid", "La Liga"),
    "barcelona": ("soccer", "esp.1", "Barcelona", "La Liga"),
    "barca": ("soccer", "esp.1", "Barcelona", "La Liga"),
    "atletico": ("soccer", "esp.1", "Atlético Madrid", "La Liga"),
    "atletico madrid": ("soccer", "esp.1", "Atlético Madrid", "La Liga"),
    "sevilla": ("soccer", "esp.1", "Sevilla", "La Liga"),
    "valencia": ("soccer", "esp.1", "Valencia", "La Liga"),
    "villarreal": ("soccer", "esp.1", "Villarreal", "La Liga"),
    "real sociedad": ("soccer", "esp.1", "Real Sociedad", "La Liga"),
    # === SOCCER (Bundesliga) ===
    "bayern": ("soccer", "ger.1", "Bayern Munich", "Bundesliga"),
    "bayern munich": ("soccer", "ger.1", "Bayern Munich", "Bundesliga"),
    "dortmund": ("soccer", "ger.1", "Borussia Dortmund", "Bundesliga"),
    "bvb": ("soccer", "ger.1", "Borussia Dortmund", "Bundesliga"),
    "leverkusen": ("soccer", "ger.1", "Bayer Leverkusen", "Bundesliga"),
    "bayer leverkusen": ("soccer", "ger.1", "Bayer Leverkusen", "Bundesliga"),
    "leipzig": ("soccer", "ger.1", "RB Leipzig", "Bundesliga"),
    "rb leipzig": ("soccer", "ger.1", "RB Leipzig", "Bundesliga"),
    "stuttgart": ("soccer", "ger.1", "VfB Stuttgart", "Bundesliga"),
    "eintracht": ("soccer", "eng.1", "Eintracht Frankfurt", "Bundesliga"),
}


def fetch_f1_slate(scope: str = "default") -> str:
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        events = data.get("events", [])
        if not events:
            return "F1: No events found."
        events.sort(key=lambda x: x.get("date", ""))

        if scope == "next":
            for e in events:
                if e["competitions"][0]["status"]["type"]["state"] == "pre":
                    name = e.get("shortName", e.get("name", "Race"))
                    dt = datetime.strptime(e["date"][:10], "%Y-%m-%d")
                    return f"F1 NEXT: {name} ({dt.month}/{dt.day})"
            return "F1: No upcoming races scheduled."

        live_events = [
            e for e in events if e["competitions"][0]["status"]["type"]["state"] == "in"
        ]
        if live_events:
            e = live_events[0]
            name = e.get("shortName", e.get("name", "Race"))
            comps = e["competitions"][0].get("competitors", [])
            top_drivers = [
                c.get("athlete", {}).get("shortName", "Driver") for c in comps[:3]
            ]
            return f"F1 LIVE: {name} - Top 3: " + ", ".join(top_drivers)

        for e in events:
            if e["competitions"][0]["status"]["type"]["state"] == "pre":
                name = e.get("shortName", e.get("name", "Race"))
                dt = datetime.strptime(e["date"][:10], "%Y-%m-%d")
                return f"F1 NEXT: {name} ({dt.month}/{dt.day})"
        return "F1: No live or upcoming races."
    except Exception as e:
        return f"Fetch failed: {e}"


def format_event(event: dict, team_query: str = "", scope: str = "") -> str:
    comp = event["competitions"][0]
    state = comp.get("status", {}).get("type", {}).get("state", "")
    detail = comp.get("status", {}).get("type", {}).get("shortDetail", "")

    competitors = comp["competitors"]
    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

    h_abbr = home["team"].get("abbreviation", home["team"]["displayName"][:3]).upper()
    a_abbr = away["team"].get("abbreviation", away["team"]["displayName"][:3]).upper()

    h_score = home.get("score", "0")
    a_score = away.get("score", "0")

    joke_suffix = ""
    if team_query == "leafs suck":
        if state in ["in", "post"]:
            h_score_int = int(h_score) if str(h_score).isdigit() else 0
            a_score_int = int(a_score) if str(a_score).isdigit() else 0
            is_home = "Maple Leafs" in home["team"]["displayName"]
            leafs_score = h_score_int if is_home else a_score_int
            opp_score = a_score_int if is_home else h_score_int
            if leafs_score > opp_score:
                joke_suffix = " boo!"
            elif leafs_score < opp_score:
                joke_suffix = " yay!"
        elif state == "pre":
            joke_suffix = " leafs gonna lose!"

    if state == "in":
        return f"{a_abbr} {a_score}@{h_abbr} {h_score}{joke_suffix}"
    elif state == "post":
        if "postponed" in detail.lower() or "canceled" in detail.lower():
            return f"{a_abbr}@{h_abbr}({detail})"
        return f"{a_abbr} {a_score}@{h_abbr} {h_score}(F){joke_suffix}"
    else:
        if "TBD" in detail.upper() or "SCHEDULED" in detail.upper():
            event_date = event.get("date", "")
            if event_date:
                try:
                    dt = datetime.strptime(event_date[:10], "%Y-%m-%d")
                    tag = "TBD" if "TBD" in detail.upper() else "Sched"
                    if scope in ["today", "tomorrow"]:
                        t = tag
                    else:
                        t = f"{dt.month}/{dt.day} {tag}"
                except:
                    t = detail
            else:
                t = detail
        else:
            t = re.sub(r"\s+[A-Z]{3,4}$", "", detail)
            t = t.replace(" PM", "p").replace(" AM", "a").replace(":00", "")
            t = t.replace(" - ", " ")
            if scope in ["today", "tomorrow"]:
                t = re.sub(r"^\d{1,2}/\d{1,2}\s*", "", t)

        return f"{a_abbr}@{h_abbr}({t}){joke_suffix}"


def fetch_league_slate(league_key: str, scope: str = "default") -> str:
    if scope == "default":
        scope = "today"
    lookup = LEAGUE_MAP.get(league_key.lower())
    if not lookup:
        return "League not mapped."

    sport, league, display_name = lookup
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"

    if league_key.lower() == "pwhl":
        return "PWHL: Off-season (No data available)"

    now = datetime.now()
    if scope == "tomorrow":
        target = now + timedelta(days=1)
        url += f"?dates={target.strftime('%Y%m%d')}"
    elif scope in ["today", "live"]:
        url += f"?dates={now.strftime('%Y%m%d')}"
    elif scope == "next":
        start = now.strftime("%Y%m%d")
        end = (now + timedelta(days=365)).strftime("%Y%m%d")
        url += f"?dates={start}-{end}&limit=1000"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        events = data.get("events", [])
        if not events:
            return f"{display_name}: No games {scope}."

        pairs = []
        if scope == "next":
            pre_events = [
                e
                for e in events
                if e["competitions"][0]["status"]["type"]["state"] == "pre"
            ]
            if not pre_events:
                return f"{display_name}: No upcoming games scheduled."
            first_date = pre_events[0]["date"][:10]
            next_slate = [e for e in pre_events if e["date"].startswith(first_date)]
            pairs = [format_event(e, scope=scope) for e in next_slate]
            return f"{display_name} NEXT: " + ", ".join(pairs)

        for e in events:
            comp = e["competitions"][0]
            state = comp.get("status", {}).get("type", {}).get("state", "")
            if scope == "live" and state != "in":
                continue
            pairs.append(format_event(e, scope=scope))

        if not pairs:
            return (
                f"{display_name}: No {'live ' if scope=='live' else ''}games {scope}."
            )
        return f"{display_name} {scope.upper()}: " + ", ".join(pairs)
    except Exception as e:
        return (
            f"PWHL: Off-season (No data available)"
            if league_key.lower() == "pwhl"
            else f"Fetch failed: {e}"
        )


def fetch_espn_team(team_query: str, scope: str = "default") -> str:
    lookup = TEAM_MAP.get(team_query.lower())
    if not lookup:
        return f"'{team_query}' not mapped. Add it to score.py!"

    sport, league, search_name, league_label = lookup
    force_next = scope == "next"

    now = datetime.now()
    start = now.strftime("%Y%m%d")
    end = (now + timedelta(days=365)).strftime("%Y%m%d")

    def get_events(l_code):
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{l_code}/scoreboard?dates={start}-{end}&limit=1000"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8")).get("events", [])
        except:
            return []

    all_raw_events = get_events(league)
    if sport == "soccer":
        fallbacks = [
            "club.friendly",
            "eng.FA",
            "eng.league_cup",
            "eng.trphy",
            "uefa.champions",
            "uefa.europa",
        ]
        if "eng" in league:
            fallbacks.extend([l for l in ["eng.1", "eng.2", "eng.3"] if l != league])
        for fb_league in fallbacks:
            all_raw_events.extend(get_events(fb_league))

    team_events = []
    seen_event_ids = set()

    for e in all_raw_events:
        eid = e.get("id")
        if eid in seen_event_ids:
            continue
        comps = e["competitions"][0]["competitors"]
        c0 = comps[0]["team"]["displayName"].lower()
        c1 = comps[1]["team"]["displayName"].lower()
        if (
            search_name.lower() in c0
            or search_name.lower() in c1
            or "leicester" in c0
            or "leicester" in c1
        ):
            seen_event_ids.add(eid)
            team_events.append(e)

    if not team_events:
        return f"[{league_label}] No games scheduled for {search_name}."

    team_events.sort(key=lambda x: x.get("date", ""))

    pre = [
        e
        for e in team_events
        if e["competitions"][0]["status"]["type"]["state"] == "pre"
    ]
    live = [
        e
        for e in team_events
        if e["competitions"][0]["status"]["type"]["state"] == "in"
    ]
    post = [
        e
        for e in team_events
        if e["competitions"][0]["status"]["type"]["state"] == "post"
    ]

    if force_next:
        if live:
            return f"[{league_label}] Live Now: " + format_event(
                live[0], team_query, scope
            )
        if pre:
            return f"[{league_label}] Next: " + format_event(pre[0], team_query, scope)
        return f"[{league_label}] No upcoming games scheduled for {search_name}."

    msg_parts = []
    if live:
        msg_parts.append(format_event(live[0], team_query, scope))
    else:
        if post:
            recent_game = post[-1]
            if recent_game["date"][:10] == now.strftime("%Y-%m-%d"):
                msg_parts.append(format_event(recent_game, team_query, scope))
        if pre:
            msg_parts.append("Next: " + format_event(pre[0], team_query, scope))

    if msg_parts:
        return f"[{league_label}] " + " | ".join(msg_parts)

    return f"[{league_label}] No recent or upcoming data for {search_name}."


@command("score", help="Get sports scores or live slates")
async def score(ctx: Context) -> str:
    who = ctx.sender_name or "you"

    query = ""
    if hasattr(ctx, "args") and ctx.args:
        if isinstance(ctx.args, str):
            query = ctx.args
        elif isinstance(ctx.args, (list, tuple)):
            query = " ".join(str(a) for a in ctx.args)
        else:
            query = str(ctx.args)

    query = query.strip()

    if not query:
        return f"@[{who}] Try !score help for commands. Leagues: {', '.join(VALID_LEAGUES)}"

    parts = query.lower().split()

    # Handle !score help
    if parts[0] == "help":
        return f"@[{who}] !score help: [team] OR [league] today/tomorrow/next/live. Leagues: {', '.join(VALID_LEAGUES)}"

    # Handle bare !score live
    if parts[0] == "live" and len(parts) == 1:
        return f"@[{who}] Use format !score [league] live (e.g. !score mlb live). Leagues: {', '.join(VALID_LEAGUES)}"

    scope = "default"
    league_or_team = query.lower()

    if parts[-1] in ["today", "tomorrow", "next", "live"]:
        scope = parts[-1]
        league_or_team = " ".join(parts[:-1])

    league_or_team = league_or_team.strip()

    if not league_or_team:
        return f"@[{who}] Specify team or league. (e.g. !score jays, !score mlb live)"

    try:
        if league_or_team in AMBIGUOUS_MAP:
            score_text = AMBIGUOUS_MAP[league_or_team]
        elif league_or_team == "f1":
            score_text = await asyncio.to_thread(fetch_f1_slate, scope)
        elif league_or_team in LEAGUE_MAP:
            score_text = await asyncio.to_thread(
                fetch_league_slate, league_or_team, scope
            )
        elif league_or_team in TEAM_MAP:
            score_text = await asyncio.to_thread(
                fetch_espn_team, team_query=league_or_team, scope=scope
            )
        else:
            score_text = f"'{league_or_team}' not mapped. Try !score help"

        msg = f"@[{who}] {score_text}"
    except Exception:
        msg = f"@[{who}] Error fetching scores."

    if len(msg) > 141:
        msg = msg[:138] + "..."

    return msg
