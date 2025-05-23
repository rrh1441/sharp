# worker.py ────────────────────────────────────────────────────────────
from __future__ import annotations

import base64, itertools, json, os, re, time, uuid
from email import message_from_bytes
from pathlib import Path
from typing import Dict, List

import requests                    # only used by gmail API; already in image
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from agent.parse_tip import TipPayload, UnmappedTeamError, parse_tip_email
from agent.team_map   import TEAM_CODE
from tools.odds_tool  import check_odds
from tools.wagerattack import place_straight          # ← REAL sportsbook call
from tools.ledger_tool import append

# ───────────────────────── configuration ────────────────────────────
UNIT_USD    = float(os.getenv("UNIT_USD", "10"))
LABEL_ID    = os.environ["GMAIL_LABEL"]          # Gmail label ID to watch
POLL_SECS   = 30
MAX_LOG_ERR = 5
DEBUG       = False

# token & history live in Fly volume
DATA_DIR = Path("/data")
DATA_DIR.mkdir(exist_ok=True, parents=True)
HIST_F   = DATA_DIR / ".gmail_hist"

creds = Credentials.from_authorized_user_info(
    json.loads(os.environ["GMAIL_TOKEN_JSON"])
)
gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)

# ───────────────────────── gmail helpers ────────────────────────────
def _save_hist(hid: str) -> None:
    HIST_F.write_text(hid, encoding="utf-8")

def _load_hist() -> str | None:
    return HIST_F.read_text(encoding="utf-8") if HIST_F.exists() else None

def _baseline() -> List[Dict]:
    hid = gmail.users().getProfile(userId="me").execute()["historyId"]
    _save_hist(hid)
    resp = gmail.users().messages().list(
        userId="me", labelIds=[LABEL_ID], maxResults=50
    ).execute()
    return resp.get("messages", [])

def _incremental(start: str) -> List[Dict]:
    resp = gmail.users().history().list(
        userId="me",
        startHistoryId=start,
        labelId=LABEL_ID,
        historyTypes=["messageAdded"],
    ).execute()
    if "historyId" in resp:
        _save_hist(resp["historyId"])
    return [
        m["message"]
        for h in resp.get("history", [])
        for m in h.get("messagesAdded", [])
    ]

def _msg_body(mid: str) -> str:
    """Return a plain-text body for Gmail message *mid*."""
    raw = gmail.users().messages().get(
        userId="me", id=mid, format="raw"
    ).execute()["raw"]
    eml = message_from_bytes(base64.urlsafe_b64decode(raw))

    # 1️⃣ text/plain part?
    if eml.is_multipart():
        for part in eml.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")

    # 2️⃣ fall back to html → text
    html = None
    if eml.is_multipart():
        for part in eml.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        html = eml.get_payload(decode=True).decode(errors="ignore")

    if html:
        return BeautifulSoup(html, "html.parser").get_text("\n")

    # 3️⃣ raw
    return eml.get_payload(decode=True).decode(errors="ignore")

# ───────────────────── tip-line extraction helpers ──────────────────
_RE_HTML  = re.compile(r"^\s*<", re.A)
_RE_UNITS = re.compile(r"\(?\s*(\d(?:\.\d)?)\s*(?:U|UNITS?)\s*\)?", re.I)
_ALIAS_PAT = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in TEAM_CODE) + r")\b", re.I
)

def _collapse_units(text: str) -> List[str]:
    """
    Collapse “bet” and “units” lines into atomic tip rows.
    Filters out header/footer noise by requiring a team alias.
    """
    clean = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip() and not _RE_HTML.match(ln) and _ALIAS_PAT.search(ln)
    ]

    bets, i = [], 0
    while i < len(clean):
        ln = clean[i]
        if _RE_UNITS.search(ln):
            bets.append(ln)
            i += 1
        elif i + 1 < len(clean) and _RE_UNITS.fullmatch(clean[i + 1]):
            bets.append(f"{ln} ({clean[i + 1]})")
            i += 2
        else:
            i += 1
    return bets

# ───────────────────── quota-safe error logging ─────────────────────
_error_counter = itertools.count()

def _log_failure(body: str, status: str, mid: str) -> None:
    idx = next(_error_counter)
    if idx < MAX_LOG_ERR:
        append(
            dict(event=body[:40], units=None, stake_usd=None,
                 confirmed_odds=None, status=status, bet_id=mid)
        )
    elif idx == MAX_LOG_ERR:
        append(
            dict(event="…more errors", units=None, stake_usd=None,
                 confirmed_odds=None, status="SKIPPED_ERRORS", bet_id="")
        )

# ───────────────────────── core processing ──────────────────────────
def _process(mid: str, tip_line: str) -> None:
    try:
        tip: TipPayload = parse_tip_email(tip_line)
    except UnmappedTeamError as e:
        _log_failure(tip_line, f"UNMAPPED_{e}", mid)
        return
    except Exception as e:
        _log_failure(tip_line, f"PARSER_ERR:{e.__class__.__name__}", mid)
        return

    stake = tip.units * UNIT_USD
    event = f"{tip.team} @ {tip.opponent or 'TBD'}"

    # optional slippage guard
    if tip.min_odds:
        ok = check_odds(event, tip.team, tip.min_odds)
        if not ok["available"]:
            append(
                dict(event=event, units=tip.units, stake_usd=stake,
                     confirmed_odds=ok["current_odds"],
                     status="SKIPPED_SLIPPAGE", bet_id=mid)
            )
            return

    # ── actual bet – converts team/market into WA rotation & fires ──
    try:
        bet = place_straight(tip.team, stake, tip.market)
    except Exception as exc:
        _log_failure(event, f"BET_ERR:{exc.__class__.__name__}", mid)
        return

    append(
        dict(event=event, units=tip.units, stake_usd=stake,
             confirmed_odds=bet["odds"], status=bet["status"],
             bet_id=bet["id"])
    )

# ───────────────────────────── main loop ────────────────────────────
def main() -> None:
    print("⏳ worker polling Gmail… (Ctrl-C to quit)")
    while True:
        msgs = _incremental(_load_hist()) if _load_hist() else _baseline()
        for m in msgs:
            body = _msg_body(m["id"])
            for tip in _collapse_units(body):
                _process(m["id"], tip)
        time.sleep(POLL_SECS)

if __name__ == "__main__":
    main()