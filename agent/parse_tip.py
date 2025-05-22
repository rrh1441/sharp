# agent/parse_tip.py
# ──────────────────────────────────────────────────────────────────────
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from agent.team_map import TEAM_CODE


class UnmappedTeamError(ValueError):
    """Raised when a nickname/city is not in TEAM_CODE."""


@dataclass(slots=True)
class TipPayload:
    units: int
    team: str                     # 3-letter code we are betting on
    opponent: Optional[str]       # 3-letter code or None
    kickoff_iso: str              # ISO UTC timestamp (placeholder)
    market: Literal["ML", "SPREAD", "TOTAL"]
    line: float | None            # spread ±n.n or total n.n
    o_u: Literal["OVER", "UNDER", None]
    min_odds: float | None


# ── regexes ───────────────────────────────────────────────────────────
RE_UNITS   = re.compile(r"\(?\s*(\d)\s*(?:U|UNITS?)\s*\)?", re.I)
RE_SPREAD  = re.compile(r"([A-Z& ]+?)\s*([+-]\d+(?:\.\d+)?)")
RE_ML      = re.compile(r"([A-Z& ]+?)\s*ML", re.I)
RE_TOTAL   = re.compile(
    r"([A-Z&]+)\s*/\s*([A-Z& ]+?)\s+(OVER|UNDER)\s+(\d+(?:\.\d+)?)", re.I
)
RE_MINODS  = re.compile(r"min[_\s-]?odds[:\s]*([\d.]+)", re.I)


def _code(raw: str) -> str:
    key = raw.upper().strip()
    if key not in TEAM_CODE:
        raise UnmappedTeamError(key)
    return TEAM_CODE[key]


# ── main parser ───────────────────────────────────────────────────────
def parse_tip_email(text: str) -> TipPayload:
    # units – mandatory
    m_units = RE_UNITS.search(text)
    if not m_units:
        raise ValueError("Could not find units")
    units = int(m_units.group(1))

    # 1) Totals   (Team / Team OVER|UNDER n.n)
    m = RE_TOTAL.search(text)
    if m:
        raw_a, raw_b, o_u, total = m.groups()
        team_a, team_b = _code(raw_a), _code(raw_b)
        pick = team_a                    # we tie bet to first team – fine for totals
        return TipPayload(
            units=units,
            team=pick,
            opponent=team_b,
            kickoff_iso=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            market="TOTAL",
            line=float(total),
            o_u=o_u.upper(),
            min_odds=None,
        )

    # 2) Spreads
    m = RE_SPREAD.search(text)
    if m:
        raw_team, line_str = m.groups()
        sel = _code(raw_team)
        return TipPayload(
            units=units,
            team=sel,
            opponent=None,
            kickoff_iso=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            market="SPREAD",
            line=float(line_str),
            o_u=None,
            min_odds=None,
        )

    # 3) Money-line
    m = RE_ML.search(text)
    if m:
        raw_team = m.group(1)
        sel = _code(raw_team)
        min_odds = (
            float(RE_MINODS.search(text).group(1))  # type: ignore[arg-type]
            if RE_MINODS.search(text)
            else None
        )
        return TipPayload(
            units=units,
            team=sel,
            opponent=None,
            kickoff_iso=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            market="ML",
            line=None,
            o_u=None,
            min_odds=min_odds,
        )

    raise ValueError("No ML, spread, or total pattern found")
