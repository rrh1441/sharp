"""
tools.bet_tool
──────────────
Real WagerAttack straight-bet integration with automatic token refresh.

External env / secrets
──────────────────────
WA_USER    – player-ID (e.g. WGT66503)
WA_PASS    – password
"""

from __future__ import annotations

import base64, json, os, time
from typing import Dict, Any

import requests
from jwt import decode as jwt_decode, ExpiredSignatureError

_BASE    = "https://wager.wagerattack.ag"
_LOGIN   = f"{_BASE}/cloud/api/Player/validPassword"
_INSERT  = f"{_BASE}/cloud/api/WagerSport/insertWagerStraight"

_USER = os.environ["WA_USER"]
_PASS = os.environ["WA_PASS"]

# in-memory session data
_session: dict[str, Any] = {
    "bearer": None,
    "php":    None,
    "exp":    0.0,          # unix secs
}

# ─────────────────────────────────────────────────────────────────────
def _login() -> None:
    """POST the same JSON the site sends on login; cache token + cookie."""
    resp = requests.post(
        _LOGIN,
        json={"customerID": _USER, "password": _PASS},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    token = data["token"]
    php   = resp.cookies.get("PHPSESSID")

    # decode expiry (saves one network call later)
    payload = jwt_decode(token, options={"verify_signature": False})
    _session.update(
        bearer=token,
        php=php,
        exp=payload["exp"],
    )
    if os.getenv("DEBUG_BET"):
        ttl = int((_session["exp"] - time.time()) / 60)
        print(f"[bet_tool] got new token, valid for {ttl}-min")

def _ensure_token() -> None:
    """Fetch/refresh if missing or <5 min from expiry."""
    if _session["bearer"] and time.time() < _session["exp"] - 300:
        return
    _login()

# ─────────────────────────────────────────────────────────────────────
def place_bet(event: str, team: str, stake: float) -> Dict:
    """
    Submit a straight bet. Returns WagerAttack's ticket details.
    Raises requests.HTTPError if the book rejects it.
    """
    _ensure_token()

    # 🌱 you still need a mapper: (event, team) ⇒ native WA line object
    # For now hard-code a dummy NBA line so you can see the ticket flow.
    dummy_ticket = {
        "customerID": _USER,
        "docNum": 14052978,                     # rotation number etc.
        "sportType": "Basketball",
        "sportSubType": "NBA",
        "riskAmount": stake,
        "winAmount": round(stake * 0.91, 2),   # -110
        # … (everything else exactly as captured in your cURL)
    }

    resp = requests.post(
        _INSERT,
        headers={
            "Authorization": f"Bearer {_session['bearer']}",
            "Content-Type":  "application/x-www-form-urlencoded; charset=UTF-8",
        },
        cookies={"PHPSESSID": _session["php"]},
        data={
            "customerID": _USER,
            "list": json.dumps([dummy_ticket]),
            "agentView": "false",
            "operation": "insertWagerStraight",
            "agentSite": "0",
        },
        timeout=10,
    )

    # automatic retry if token really did expire between check and send
    if resp.status_code == 401:
        _login()
        return place_bet(event, team, stake)

    resp.raise_for_status()
    return {"status": "PLACED", "id": resp.json().get("ticket")}