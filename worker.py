# worker.py
# ──────────────────────────────────────────────────────────────────────
from __future__ import annotations

import base64
import itertools
import json
import os
import re
import time
import uuid
from email import message_from_bytes
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from agent.parse_tip import TipPayload, UnmappedTeamError, parse_tip_email
from agent.team_map import TEAM_CODE                     # ← new (for alias filter)
from tools.odds_tool import check_odds
from tools.ledger_tool import append

# ---------------------------------------------------------------------
# TEMPORARY stub — replace with real sportsbook integration later
def place_bet(event: str, team: str, stake: float) -> Dict:
    """
    Dry-run bet stub. Always “succeeds” and returns a fake ID/odds.
    Replace this with a real call to WagerAttack once we’re confident.
    """
    return {
        "id": str(uuid.uuid4()),
        "odds": None,
        "status": "DRYRUN",
    }
# ---------------------------------------------------------------------


# ── config ────────────────────────────────────────────────────────────
UNIT_USD    = float(os.getenv("UNIT_USD", "10"))
LABEL_ID    = os.environ["GMAIL_LABEL"]               # Gmail label ID to watch
POLL_SECS   = 30                                      # inbox poll interval
MAX_LOG_ERR = 5                                       # cap on error rows / run
DEBUG       = False

creds = Credentials.from_authorized_user_info(json.loads(os.environ["GMAIL_TOKEN_JSON"]))
gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)

HIST_F = Path(".gmail_hist")                          # stores last historyId


# ── gmail helpers ────────────────────────────────────────────────────
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
    """
    Return **plain-text** body for a Gmail message ID.
    If only HTML exists (FanBasis template), strip tags with BeautifulSoup.
    """
    raw = gmail.users().messages().get(userId="me", id=mid, format="raw").execute()["raw"]
    eml = message_from_bytes(base64.urlsafe_b64decode(raw))

    # 1️⃣ text/plain part first
    if eml.is_multipart():
        for part in eml.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")

    # 2️⃣ fall back to HTML → text
    html = eml.get_payload(decode=True).decode(errors="ignore") if not eml.is_multipart() else None
    if eml.is_multipart():
        for part in eml.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode(errors="ignore")
                break

    if html:
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text("\n")           # keep line breaks for regex

    # 3️⃣ last-ditch: raw payload
    return eml.get_payload(decode=True).decode(errors="ignore")


# ── tip-line extraction  ────────────────────────────────────────────
_RE_HTML  = re.compile(r"^\s*<", re.A)
_RE_UNITS = re.compile(r"\(?\s*(\d(?:\.\d)?)\s*(?:U|UNITS?)\s*\)?", re.I)

# compile one big pattern of all team aliases for fast filtering
_ALIAS_PAT = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in TEAM_CODE.keys()) + r")\b",
    re.I,
)


def _collapse_units(text: str) -> List[str]:
    """
    Collapse “bet” and “units” into single lines.

    • Ignores header/footer lines that don’t mention a team alias
    • Supports units inline (“Padres ML 1u”) OR on next line
    """
    clean = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip()                           # non-empty
        and not _RE_HTML.match(ln)              # not raw HTML
        and _ALIAS_PAT.search(ln)               # contains a team keyword
    ]

    bets, i = [], 0
    while i < len(clean):
        ln = clean[i]
        if _RE_UNITS.search(ln):                       # units already present
            bets.append(ln)
            i += 1
        elif i + 1 < len(clean) and _RE_UNITS.fullmatch(clean[i + 1]):
            bets.append(f"{ln} ({clean[i + 1]})")      # merge with next-line units
            i += 2
        else:
            i += 1
    return bets


# ── logging helper (quota safe) ─────────────────────────────────────
_error_counter = itertools.count()


def _log_failure(body: str, status: str, mid: str) -> None:
    """
    Record at most MAX_LOG_ERR rows per run to avoid Sheets API quota hits.
    """
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
    event = f"{tip.team} @ {tip.opponent or 'TBD'}"  # opponent can be None

    # ── odds slippage guard (if tip included “min_odds”) ──
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

    # ── Dry-run bet placement ──
    bet = place_bet(event, tip.team, stake)
    append(
        {
            "event": event,
            "units": tip.units,
            "stake_usd": stake,
            "confirmed_odds": bet.get("odds"),
            "status": bet.get("status", "DRYRUN"),
            "bet_id": bet.get("id", mid),
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