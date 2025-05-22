"""
agent.team_map
──────────────
Canonical team codes for every club likely to appear in NC Sharp emails.

• NBA / MLB / NFL → official three-letter feed abbreviations
• NHL            → three-letter club codes (OddsAPI’s convention)

Both abbreviations *and* full-length city / nickname aliases map to the same
code so any reasonable phrasing parses cleanly.
"""

from __future__ import annotations

# ────────────────────────────────────────────────────────────────────
# master map  →  key = ANY alias (uppercase, punctuation ignored)
# ────────────────────────────────────────────────────────────────────
TEAM_CODE: dict[str, str] = {
    # ────────── NBA ──────────
    "ATLANTA": "ATL", "HAWKS": "ATL",
    "BOSTON": "BOS", "CELTICS": "BOS",
    "BROOKLYN": "BKN", "NETS": "BKN",
    "CHARLOTTE": "CHA", "HORNETS": "CHA",
    "CHICAGO": "CHI", "BULLS": "CHI",
    "CLEVELAND": "CLE", "CAVALIERS": "CLE", "CAVS": "CLE",
    "DALLAS": "DAL", "MAVERICKS": "DAL", "MAVS": "DAL",
    "DENVER": "DEN", "NUGGETS": "DEN",
    "DETROIT": "DET", "PISTONS": "DET",
    "GOLDEN STATE": "GSW", "WARRIORS": "GSW", "GS": "GSW",
    "HOUSTON": "HOU", "ROCKETS": "HOU",
    "INDIANA": "IND", "PACERS": "IND",
    "LOS ANGELES LAKERS": "LAL", "L.A. LAKERS": "LAL", "LAKERS": "LAL",
    "LOS ANGELES CLIPPERS": "LAC", "L.A. CLIPPERS": "LAC", "CLIPPERS": "LAC",
    "MEMPHIS": "MEM", "GRIZZLIES": "MEM",
    "MIAMI": "MIA", "HEAT": "MIA",
    "MILWAUKEE": "MIL", "BUCKS": "MIL",
    "MINNESOTA": "MIN", "TIMBERWOLVES": "MIN", "T-WOLVES": "MIN",
    "NEW ORLEANS": "NOP", "PELICANS": "NOP", "NO": "NOP",
    "NEW YORK": "NYK", "KNICKS": "NYK", "NEW YORK KNICKS": "NYK",
    "OKLAHOMA CITY": "OKC", "THUNDER": "OKC",
    "ORLANDO": "ORL", "MAGIC": "ORL",
    "PHILADELPHIA": "PHI", "SIXERS": "PHI", "76ERS": "PHI",
    "PHOENIX": "PHX", "SUNS": "PHX",
    "PORTLAND": "POR", "TRAIL BLAZERS": "POR", "BLAZERS": "POR",
    "SACRAMENTO": "SAC", "KINGS": "SAC",
    "SAN ANTONIO": "SAS", "SPURS": "SAS",
    "TORONTO": "TOR", "RAPTORS": "TOR",
    "UTAH": "UTA", "JAZZ": "UTA",
    "WASHINGTON": "WAS", "WIZARDS": "WAS",

    # ────────── MLB ──────────
    "ARIZONA": "ARI", "ARIZONA DIAMONDBACKS": "ARI", "DIAMONDBACKS": "ARI", "D-BACKS": "ARI",
    "ATLANTA": "ATL", "BRAVES": "ATL",
    "BALTIMORE": "BAL", "ORIOLES": "BAL", "O'S": "BAL",
    "BOSTON": "BOS", "RED SOX": "BOS",
    "CHI CUBS": "CHC", "CUBS": "CHC",
    "CHI WHITE SOX": "CWS", "WHITE SOX": "CWS", "SOX": "CWS",
    "CINCINNATI": "CIN", "REDS": "CIN",
    "CLEVELAND": "CLE", "GUARDIANS": "CLE", "INDIANS": "CLE",
    "COLORADO": "COL", "ROCKIES": "COL",
    "DETROIT": "DET", "DETROIT TIGERS": "DET", "TIGERS": "DET",
    "HOUSTON": "HOU", "ASTROS": "HOU",
    "KANSAS CITY": "KC", "ROYALS": "KC",
    "LA ANGELS": "LAA", "ANGELS": "LAA",
    "LA DODGERS": "LAD", "DODGERS": "LAD",
    "MIAMI": "MIA", "MARLINS": "MIA",
    "MILWAUKEE": "MIL", "BREWERS": "MIL",
    "MINNESOTA": "MIN", "TWINS": "MIN",
    "NY METS": "NYM", "METS": "NYM",
    "NY YANKEES": "NYY", "YANKEES": "NYY",
    "OAKLAND": "OAK", "ATHLETICS": "OAK", "A'S": "OAK",
    "PHILADELPHIA": "PHI", "PHILLIES": "PHI", "PHILS": "PHI",
    "PITTSBURGH": "PIT", "PIRATES": "PIT", "BUCS": "PIT",
    "SAN DIEGO": "SD", "PADRES": "SD",
    "SAN FRANCISCO": "SF", "GIANTS": "SF",
    "SEATTLE": "SEA", "MARINERS": "SEA", "M'S": "SEA",
    "ST LOUIS": "STL", "ST LOUIS CARDINALS": "STL", "CARDINALS": "STL", "CARDS": "STL",
    "TAMPA BAY": "TB", "RAYS": "TB",
    "TEXAS": "TEX", "RANGERS": "TEX",
    "TORONTO": "TOR", "BLUE JAYS": "TOR", "JAYS": "TOR",
    "WASHINGTON": "WSH", "NATIONALS": "WSH", "NATS": "WSH",

    # ────────── NFL ──────────
    "ARIZONA CARDINALS": "ARI", "CARDINALS": "ARI",
    "ATLANTA FALCONS": "ATL", "FALCONS": "ATL",
    "BALTIMORE RAVENS": "BAL", "RAVENS": "BAL",
    "BUFFALO BILLS": "BUF", "BILLS": "BUF",
    "CAROLINA PANTHERS": "CAR", "PANTHERS": "CAR",
    "CHICAGO BEARS": "CHI", "BEARS": "CHI",
    "CINCINNATI BENGALS": "CIN", "BENGALS": "CIN",
    "CLEVELAND BROWNS": "CLE", "BROWNS": "CLE",
    "DALLAS COWBOYS": "DAL", "COWBOYS": "DAL",
    "DENVER BRONCOS": "DEN", "BRONCOS": "DEN",
    "DETROIT LIONS": "DET", "LIONS": "DET",
    "GREEN BAY PACKERS": "GB", "PACKERS": "GB",
    "HOUSTON TEXANS": "HOU", "TEXANS": "HOU",
    "INDIANAPOLIS COLTS": "IND", "COLTS": "IND",
    "JACKSONVILLE JAGUARS": "JAX", "JAGUARS": "JAX", "JAGS": "JAX",
    "KANSAS CITY CHIEFS": "KC", "CHIEFS": "KC",
    "LAS VEGAS RAIDERS": "LV", "RAIDERS": "LV",
    "LA CHARGERS": "LAC", "CHARGERS": "LAC",
    "LA RAMS": "LAR", "RAMS": "LAR",
    "MIAMI DOLPHINS": "MIA", "DOLPHINS": "MIA",
    "MINNESOTA VIKINGS": "MIN", "VIKINGS": "MIN", "VIKES": "MIN",
    "NEW ENGLAND PATRIOTS": "NE", "PATRIOTS": "NE", "PATS": "NE",
    "NEW ORLEANS SAINTS": "NO", "SAINTS": "NO",
    "NEW YORK GIANTS": "NYG", "GIANTS": "NYG",
    "NEW YORK JETS": "NYJ", "JETS": "NYJ",
    "PHILADELPHIA EAGLES": "PHI", "EAGLES": "PHI",
    "PITTSBURGH STEELERS": "PIT", "STEELERS": "PIT", "STEEL": "PIT",
    "SAN FRANCISCO 49ERS": "SF", "49ERS": "SF", "NINERS": "SF",
    "SEATTLE SEAHAWKS": "SEA", "SEAHAWKS": "SEA", "HAWKS": "SEA",
    "TAMPA BAY BUCCANEERS": "TB", "BUCCANEERS": "TB", "BUCS": "TB",
    "TENNESSEE TITANS": "TEN", "TITANS": "TEN",
    "WASHINGTON COMMANDERS": "WAS", "COMMANDERS": "WAS", "WFT": "WAS",

    # ────────── NHL ──────────
    "ANAHEIM": "ANA", "DUCKS": "ANA",
    "ARIZONA COYOTES": "ARI", "COYOTES": "ARI", "YOTES": "ARI",
    "BOSTON BRUINS": "BOS", "BRUINS": "BOS",
    "BUFFALO SABRES": "BUF", "SABRES": "BUF",
    "CALGARY FLAMES": "CGY", "FLAMES": "CGY",
    "CAROLINA HURRICANES": "CAR", "HURRICANES": "CAR", "CANES": "CAR",
    "CHICAGO BLACKHAWKS": "CHI", "BLACKHAWKS": "CHI", "HAWKS": "CHI",
    "COLORADO AVALANCHE": "COL", "AVALANCHE": "COL", "AVS": "COL",
    "COLUMBUS BLUE JACKETS": "CBJ", "BLUE JACKETS": "CBJ", "JACKETS": "CBJ",
    "DALLAS STARS": "DAL", "STARS": "DAL",
    "DETROIT RED WINGS": "DET", "RED WINGS": "DET", "WINGS": "DET",
    "EDMONTON OILERS": "EDM", "OILERS": "EDM",
    "FLORIDA PANTHERS": "FLA", "PANTHERS": "FLA", "CATS": "FLA",
    "LA KINGS": "LAK", "KINGS": "LAK",
    "MINNESOTA WILD": "MIN", "WILD": "MIN",
    "MONTREAL CANADIENS": "MTL", "CANADIENS": "MTL", "HABS": "MTL",
    "NASHVILLE PREDATORS": "NSH", "PREDATORS": "NSH", "PREDS": "NSH",
    "NEW JERSEY DEVILS": "NJD", "DEVILS": "NJD",
    "NY ISLANDERS": "NYI", "ISLANDERS": "NYI", "ISLES": "NYI",
    "NY RANGERS": "NYR", "RANGERS": "NYR",
    "OTTAWA SENATORS": "OTT", "SENATORS": "OTT", "SENS": "OTT",
    "PHILADELPHIA FLYERS": "PHI", "FLYERS": "PHI",
    "PITTSBURGH PENGUINS": "PIT", "PENGUINS": "PIT", "PENS": "PIT",
    "SAN JOSE SHARKS": "SJS", "SHARKS": "SJS",
    "SEATTLE KRAKEN": "SEA", "KRAKEN": "SEA",
    "ST LOUIS BLUES": "STL", "BLUES": "STL",
    "TAMPA BAY LIGHTNING": "TBL", "LIGHTNING": "TBL", "BOLTS": "TBL",
    "TORONTO MAPLE LEAFS": "TOR", "MAPLE LEAFS": "TOR", "LEAFS": "TOR",
    "VANCOUVER CANUCKS": "VAN", "CANUCKS": "VAN", "NUCKS": "VAN",
    "VEGAS GOLDEN KNIGHTS": "VGK", "GOLDEN KNIGHTS": "VGK", "KNIGHTS": "VGK",
    "WASHINGTON CAPITALS": "WSH", "CAPITALS": "WSH", "CAPS": "WSH",
    "WINNIPEG JETS": "WPG", "JETS": "WPG",
}

# -------------------------------------------------------------------
# reverse helper (code → primary alias) — handy for logging / UI
# -------------------------------------------------------------------
CODE_TO_PRIMARY = {
    code: next(alias for alias, c in TEAM_CODE.items() if c == code)
    for code in set(TEAM_CODE.values())
}