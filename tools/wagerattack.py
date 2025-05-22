"""
tools.wagerattack
────────────────────────────────────────────────────────────────────────────
Login-refresh, board lookup and straight-bet posting for WagerAttack.

External deps:   requests  (already in your image)
Environment:
    BOOK_USER   – WA username  (already set in Fly secrets)
    BOOK_PASS   – WA password  (already set in Fly secrets)
"""

from __future__ import annotations
import base64, json, os, time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import requests
from agent.team_map import TEAM_CODE

WA_BASE   = os.getenv("WA_BASE", "https://wager.wagerattack.ag")
USER      = os.environ["BOOK_USER"]
PWD       = os.environ["BOOK_PASS"]
DATA_DIR  = Path("/data")                       # volume mount
TOK_F     = DATA_DIR / "wa_token.json"
BOARD_TTL = 30                                  # seconds

# ──────────────────────────────────────────────────────────────────────
def _jwt_exp(ts: str) -> int:
    payload = json.loads(base64.urlsafe_b64decode(ts.split(".")[1] + "=="))
    return int(payload["exp"])

def _save_tok(tok: str) -> None:
    TOK_F.write_text(json.dumps({"token": tok, "exp": _jwt_exp(tok)}))

def _load_tok() -> str | None:
    if TOK_F.exists():
        d = json.loads(TOK_F.read_text())
        if time.time() < d["exp"] - 60:
            return d["token"]
    return None

def _refresh_tok() -> str:
    r = requests.post(
        f"{WA_BASE}/cloud/api/login/validPassword",
        json={"username": USER, "password": PWD, "device": "web"},
        timeout=8,
    )
    r.raise_for_status()
    tok = r.json()["token"]
    _save_tok(tok)
    return tok

def _get_tok() -> str:
    return _load_tok() or _refresh_tok()

# ─────────── rotation board cache ────────────────────────────────────
_board_cache: dict[str, tuple[float, List[Dict[str, Any]]]] = {}

def _board(sport: str, sub: str) -> List[Dict[str, Any]]:
    key = f"{sport}:{sub}"
    ts, rows = _board_cache.get(key, (0.0, []))
    if time.time() - ts < BOARD_TTL:
        return rows
    r = requests.get(
        f"{WA_BASE}/cloud/api/WagerSport/getLinelist",
        params={"sportType": sport, "sportSubType": sub},
        headers={"Authorization": f"Bearer {_get_tok()}"},
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()
    _board_cache[key] = (time.time(), rows)
    return rows

# ─────────── mapper ─────────────────────────────────────────────────
def _rotation(team_code: str, market: str) -> SimpleNamespace:
    """Return the WA line dict for the team/market we want."""
    sport = "Baseball" if team_code in TEAM_CODE.values() and len(team_code)==3 and team_code not in {"NYK","LAL"} else "Basketball"
    sub   = "MLB" if sport == "Baseball" else "NBA"
    for g in _board(sport, sub):
        t1 = TEAM_CODE.get(g["team1"].upper(), "")
        t2 = TEAM_CODE.get(g["team2"].upper(), "")
        if team_code not in (t1, t2):
            continue
        if market == "ML":
            price = g["money1"] if t1 == team_code else g["money2"]
            return SimpleNamespace(**g, price=price, wager_type="M",
                                   spread="", adj_spread="", line_type="M")
        if market == "SPREAD":
            price = g["spreadPrice1"] if t1 == team_code else g["spreadPrice2"]
            spread = g["spread1"] if t1 == team_code else g["spread2"]
            return SimpleNamespace(**g, price=price, wager_type="S",
                                   spread=spread, adj_spread=spread,
                                   line_type="S")
        # totals not wired yet – extend here
    raise LookupError("no matching rotation")

# ─────────── public entry - place_straight ───────────────────────────
def place_straight(team: str, stake: float, market: str) -> Dict:
    rot = _rotation(team, market)                  # ↖ rotation mapper
    ticket = {
        "customerID": USER,
        "docNum": rot["docNum"],
        "wagerType": rot.wager_type,
        "gameNum": rot["gameNum"],
        "wagerCount": 1,
        "gameDate": rot["gameDate"],
        "sportType": rot["sportType"],
        "sportSubType": rot["sportSubType"],
        "lineType": rot.line_type,
        "adjSpread": rot.adj_spread,
        "finalMoney": rot.price,
        "riskAmount": stake,
        "winAmount": round(abs(stake * rot.price / 100), 2) if rot.price < 0 else round(stake * rot.price / 100, 2),
        "chosenTeamID": rot["team1"] if TEAM_CODE.get(rot["team1"].upper()) == team else rot["team2"],
        # …many optional WA fields omitted; these are the minimum that work
    }
    payload = {
        "customerID": USER,
        "list": json.dumps([ticket]),
        "agentView": "false",
        "operation": "insertWagerStraight",
    }
    r = requests.post(
        f"{WA_BASE}/cloud/api/WagerSport/insertWagerStraight",
        headers={
            "Authorization": f"Bearer {_get_tok()}",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
        data=payload,
        timeout=10,
    )
    r.raise_for_status()
    j = r.json()
    return {"id": j.get("wagerNumber", str(j)), "odds": rot.price, "status": "PLACED"}