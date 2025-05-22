"""
tools/odds_tool.py
────────────────────────────────────────────────────────────────────────
Live-odds gatekeeper for WagerAttack.

Returned structure:
    {
        "available": bool,          # False only when line exists AND < threshold
        "current_odds": float | None,
        "event": str                # canonical "AWAY @ HOME"
    }
"""

from __future__ import annotations
import os, time, requests
from typing import TypedDict, Tuple, Dict

from agent.team_map import TEAM_CODE

API_KEY  = os.getenv("THEODDS_API_KEY")
SPORT    = os.getenv("ODDS_SPORT", "baseball_mlb")   # adjust per season
REGION   = "us"
MARKET   = "h2h"                                     # money-line only
SLIPPAGE = float(os.getenv("SLIPPAGE", "0.03"))      # 3 %

if not API_KEY:
    raise RuntimeError("THEODDS_API_KEY must be set")

_cache: Dict[str, Tuple[float, float]] = {}          # event -> (ts, odds)


class OddsResult(TypedDict):
    available: bool
    current_odds: float | None
    event: str


# ───────────────────────── helpers ────────────────────────────
def _codes(game: dict) -> Tuple[str, str] | None:
    """Return (AWAY, HOME) 3-letter codes or None if unmapped."""
    if "teams" in game and len(game["teams"]) == 2:
        away_raw, home_raw = game["teams"]
    elif "away_team" in game and "home_team" in game:
        away_raw, home_raw = game["away_team"], game["home_team"]
    else:
        return None
    try:
        return TEAM_CODE[away_raw.upper()], TEAM_CODE[home_raw.upper()]
    except KeyError:
        return None


def _query(sel: str) -> Tuple[float | None, str]:
    """
    Returns (odds or None, canonical_event)
    canonical_event always has the form "AWY @ HOM" if a game is found.
    """
    url = (
        f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"
        f"?apiKey={API_KEY}&regions={REGION}&markets={MARKET}&oddsFormat=decimal"
    )
    data = requests.get(url, timeout=10).json()

    for game in data:
        pair = _codes(game)
        if not pair or sel not in pair:
            continue
        away, home = pair
        canon = f"{away} @ {home}"

        # caching (per event)
        now = time.time()
        if canon in _cache and now - _cache[canon][0] < 30:
            return _cache[canon][1], canon

        for bk in game.get("bookmakers", []):
            if bk["key"] != "wagerattack":
                continue
            for mkt in bk.get("markets", []):
                for out in mkt.get("outcomes", []):
                    name_code = TEAM_CODE.get(out["name"].upper(), out["name"][:3])
                    if name_code == sel:
                        price = float(out["price"])
                        _cache[canon] = (now, price)
                        return price, canon

        return None, canon          # game found but no price for this side

    return None, ""                 # team not found in feed


# ───────────────────────── public API ──────────────────────────
def check_odds(event: str, sel: str, min_odds: float) -> OddsResult:
    """
    • If no market/odds → available=True, current_odds=None  (pass-through).
    • If odds exist    → apply slippage check.
    """
    current, canon = _query(sel)

    if current is None:            # feed missing → let bet proceed
        return {"available": True, "current_odds": None, "event": canon or event}

    available = current >= min_odds * (1 - SLIPPAGE)
    return {"available": available, "current_odds": current, "event": canon}


# ───────────────────────── smoke test ──────────────────────────
if __name__ == "__main__":
    print(check_odds("DUMMY", "PIT", 1.85))