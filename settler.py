#!/usr/bin/env python
"""
Settler – reconcile confirmed bets via TheOdds API
=================================================

Runs inside Fly Machines and updates the **status** column in the Google Sheet
(created by `tools/ledger_tool.append`) from **CONFIRMED** → **WIN** / **LOSS**.

• Works for any Odds API sport that exposes a **scores** endpoint  
• Looks back three days, which is plenty for MLB / NBA / NHL / NFL completion  
• Default cadence is once every 24 h, but you can pass `--hourly` to loop every hour
  and keep the machine running at minimal cost.

Environment Variables
---------------------
THEODDS_API_KEY    Your TheOddsAPI key
GOOGLE_SHEETS_JSON One-line JSON of the service-account credentials
SHEET_ID           44-char Google Sheet ID (same as used by `ledger_tool`)
SPORT              (optional) The OddsAPI sport key, default "baseball_mlb"
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import TypedDict, List, Dict, Any

import gspread
import requests

# ─────────────────────────────── Config ────────────────────────────── #

API_KEY   = os.environ["THEODDS_API_KEY"]
SPORT     = os.getenv("SPORT", "baseball_mlb")
SHEET_ID  = os.environ["SHEET_ID"]

_gc = gspread.service_account_from_dict(json.loads(os.environ["GOOGLE_SHEETS_JSON"]))
_ws = _gc.open_by_key(SHEET_ID).sheet1

# -------------------------------------------------------------------- #


class Score(TypedDict):
    name: str
    score: int | None  # scores can be null while game in-play


def _fetch_scores(event: str) -> List[Score] | None:
    """
    Return `[away, home]` score list for the event (`AWAY @ HOME`)
    or **None** if the game isn’t returned by TheOddsAPI yet/anymore.
    """
    url = (
        f"https://api.the-odds-api.com/v4/sports/{SPORT}/scores/"
        f"?apiKey={API_KEY}&daysFrom=3"
    )
    for game in requests.get(url, timeout=10).json():
        canonical = f"{game['away_team'].upper()} @ {game['home_team'].upper()}"
        if canonical == event:
            return game.get("scores")
    return None


def _is_win(tipped_event: str, scores: List[Score]) -> bool:
    """Given canonical event string and score payload, decide win/loss."""
    away_sc, home_sc = scores
    tipped_away = tipped_event.split(" @ ")[0]  # "PIT" from "PIT @ CHC"
    if tipped_away == away_sc["name"].upper():
        return away_sc["score"] > home_sc["score"]
    # otherwise we backed the home side
    return home_sc["score"] > away_sc["score"]


def reconcile_sheet() -> None:
    """
    Walk the sheet and flip CONFIRMED rows to WIN / LOSS when a final
    score is available.
    """
    rows: List[Dict[str, Any]] = _ws.get_all_records()
    for idx, row in enumerate(rows, start=2):  # sheet rows are 1-based
        if row["status"] != "CONFIRMED":
            continue
        scores = _fetch_scores(row["event"])
        if not scores or any(s["score"] is None for s in scores):
            continue  # game not final yet
        result = "WIN" if _is_win(row["event"], scores) else "LOSS"
        _ws.update_cell(idx, 6, result)  # column 6 = status


# ──────────────────────────────── Main ─────────────────────────────── #

def main() -> None:
    ap = argparse.ArgumentParser(description="Reconcil-bot for confirmed wagers")
    ap.add_argument("--hourly", action="store_true", help="run every hour instead of daily")
    args = ap.parse_args()

    sleep_seconds = 3600 if args.hourly else 24 * 3600

    while True:
        print("🕛  settler tick", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        try:
            reconcile_sheet()
        except Exception as exc:  # never die silently
            print("⚠️  settler error:", exc)
        time.sleep(sleep_seconds)


if __name__ == "__main__":  # pragma: no cover
    main()