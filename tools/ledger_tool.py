"""
Append wager records to the first worksheet of the Google Sheet defined
by the SHEET_ID environment variable.

Required env vars
-----------------
GOOGLE_SHEETS_JSON  One-line JSON of the Google *service-account* key
SHEET_ID            44-character Google Sheet ID
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import gspread
from dotenv import load_dotenv

# Load .env when running locally; harmless on Fly
load_dotenv()

# ── env validation ───────────────────────────────────────────────────
_SA_JSON = os.getenv("GOOGLE_SHEETS_JSON")
_SHEET_ID = os.getenv("SHEET_ID")

if not _SA_JSON or not _SHEET_ID:
    raise RuntimeError(
        "GOOGLE_SHEETS_JSON and SHEET_ID environment variables must be set."
    )

# ── client handle ────────────────────────────────────────────────────
_gc = gspread.service_account_from_dict(json.loads(_SA_JSON))
_ws = _gc.open_by_key(_SHEET_ID).sheet1  # first worksheet

_HEADER = [
    "timestamp_utc",
    "event",
    "units",
    "stake_usd",
    "confirmed_odds",
    "status",
    "bet_id",
]


def _ensure_header() -> None:
    if _ws.row_values(1) != _HEADER:
        _ws.insert_row(_HEADER, 1, value_input_option="RAW")


_ensure_header()

# ── public api ───────────────────────────────────────────────────────
def append(payload: Dict[str, Any]) -> None:
    """Append a single wager record to the sheet."""
    row: List[Any] = [
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        payload.get("event"),
        payload.get("units"),
        payload.get("stake_usd"),
        payload.get("confirmed_odds"),
        payload.get("status"),
        payload.get("bet_id"),
    ]
    _ws.append_row(row, value_input_option="USER_ENTERED")


if __name__ == "__main__":  # smoke-test
    append(
        {
            "event": "DEV @ TEST",
            "units": 1,
            "stake_usd": 0.01,
            "confirmed_odds": 1.91,
            "status": "DRYRUN",
            "bet_id": "000",
        }
    )
    print("✅  Row appended successfully")