# worker.py
# ──────────────────────────────────────────────────────────────────────
from __future__ import annotations

import base64
import itertools
import json
import os
import re
import time
from email import message_from_bytes
from pathlib import Path
from typing import Dict, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from agent.parse_tip import TipPayload, UnmappedTeamError, parse_tip_email
from tools.bet_tool import place_bet
from tools.ledger_tool import append
from tools.odds_tool import check_odds

# ── config ────────────────────────────────────────────────────────────
UNIT_USD = float(os.getenv("UNIT_USD", "10"))
LABEL_ID = os.environ["GMAIL_LABEL"]
POLL_SECS = 30
MAX_LOG_ERR = 5
DEBUG = False

creds = Credentials.from_authorized_user_info(json.loads(os.environ["GMAIL_TOKEN_JSON"]))
gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)

HIST_F = Path(".gmail_hist")

# ── gmail helpers ────────────────────────────────────────────────────
def _save_hist(hid: str) -> None:
    HIST_F.write_text(hid, encoding="utf-8")


def _load_hist() -> str | None:
    return HIST_F.read_text(encoding="utf-8") if HIST_F.exists() else None


def _baseline() -> List[Dict]:
    hid = gmail.users().getProfile(userId="me").execute()["historyId"]
    _save_hist(hid)
    resp = gmail.users().messages().list(userId="me", labelIds=[LABEL_ID], maxResults=50).execute()
    msgs = resp.get("messages", [])
    if DEBUG:
        print("[DEBUG] baseline", len(msgs))
    return msgs


def _incremental(start: str) -> List[Dict]:
    resp = gmail.users().history().list(
        userId="me",
        startHistoryId=start,
        labelId=LABEL_ID,
        historyTypes=["messageAdded"],
    ).execute()
    if "historyId" in resp:
        _save_hist(resp["historyId"])
    msgs = [m["message"] for h in resp.get("history", []) for m in h.get("messagesAdded", [])]
    if DEBUG:
        print("[DEBUG] incremental", len(msgs))
    return msgs


def _msg_body(mid: str) -> str:
    raw = gmail.users().messages().get(userId="me", id=mid, format="raw").execute()["raw"]
    eml = message_from_bytes(base64.urlsafe_b64decode(raw))
    # use the *first* text/plain part if available
    if eml.is_multipart():
        for part in eml.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    # fallback to decoded body
    return eml.get_payload(decode=True).decode(errors="ignore")


# ── tip-line extraction  ────────────────────────────────────────────
# any line that still begins with "<" after decoding is HTML noise
_RE_HTML = re.compile(r"^\s*<", re.A)
_RE_UNITS = re.compile(r"\(?\s*(\d)\s*(?:U|UNITS?)\s*\)?", re.I)

def _collapse_units(text: str) -> List[str]:
    """Return a list of self-contained bet lines (bet + units)."""
    clean = [ln.strip() for ln in text.splitlines() if ln.strip() and not _RE_HTML.match(ln)]
    bets, i = [], 0
    while i < len(clean):
        ln = clean[i]
        if _RE_UNITS.search(ln):          # units already on this line
            bets.append(ln)
            i += 1
        elif i + 1 < len(clean) and _RE_UNITS.fullmatch(clean[i + 1]):
            bets.append(f"{ln} ({clean[i + 1]})")
            i += 2
        else:                             # skip unrelated line
            i += 1
    return bets


# ── logging helper (quota safe) ─────────────────────────────────────
_error_counter = itertools.count()

def _log_failure(body: str, status: str, mid: str) -> None:
    """Record at most MAX_LOG_ERR rows per run to avoid Sheets API quota hits."""
    idx = next(_error_counter)
    if idx < MAX_LOG_ERR:
        append(
            {
                "event": body[:40],
                "units": None,
                "stake_usd": None,
                "confirmed_odds": None,
                "status": status,
                "bet_id": mid,
            }
        )
    elif idx == MAX_LOG_ERR:
        append(
            {
                "event": "…more errors",
                "units": None,
                "stake_usd": None,
                "confirmed_odds": None,
                "status": "SKIPPED_ERRORS",
                "bet_id": "",
            }
        )


# ── core processing ────────────────────────────────────────────────
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

    # Construct a minimal event string for odds lookup.  
    # opponent may be None → "TBD"
    event = f"{tip.team} @ {tip.opponent or 'TBD'}"

    # odds-check (only if min_odds was present)
    if tip.min_odds:
        ok = check_odds(event, tip.team, tip.min_odds)
        if not ok["available"]:
            append(
                {
                    "event": event,
                    "units": tip.units,
                    "stake_usd": stake,
                    "confirmed_odds": ok["current_odds"],
                    "status": "SKIPPED_SLIPPAGE",
                    "bet_id": mid,
                }
            )
            return

    try:
        bet = place_bet(event, tip.team, stake)
        append(
            {
                "event": event,
                "units": tip.units,
                "stake_usd": stake,
                "confirmed_odds": bet.get("odds"),
                "status": "PLACED",
                "bet_id": bet.get("id", mid),
            }
        )
    except Exception as exc:
        append(
            {
                "event": event,
                "units": tip.units,
                "stake_usd": stake,
                "confirmed_odds": None,
                "status": "BET_ERROR",
                "bet_id": f"{mid} – {exc.__class__.__name__}",
            }
        )


# ── main loop ───────────────────────────────────────────────────────
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