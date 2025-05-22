"""
agent.parse_tip
───────────────
Convert one cleaned “bet line” into a structured TipPayload.

Accepted formats
────────────────
• Money-line :  "Padres ML (2U)"      | "St Louis Cardinals ML"
• Spread     :  "Knicks -4 (1U)"      | "NYR +1.5"
• Total      :  "Padres / Jays UNDER 9 (1.5U)"

Extras
──────
• Units may trail on the same line **or** be the next separate line.
• O/U bets treat the first listed team as “team”, the second as opponent.
• “min_odds: +120” (optional) is captured for ML bets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from agent.team_map import TEAM_CODE


class UnmappedTeamError(ValueError):
    ...


@dataclass(slots=True)
class TipPayload:
    units: float
    team: str                     # 3-letter code we are backing
    opponent: Optional[str]       # 3-letter code or None
    kickoff_iso: str              # placeholder timestamp
    market: Literal["ML", "SPREAD", "TOTAL"]
    line: float | None            # spread ±n.n or total n.n
    o_u: Literal["OVER", "UNDER", None]
    min_odds: float | None        # ML only


# ── regex helpers ───────────────────────────────────────────────────
_UNITS_RE  = re.compile(r"\(?\s*([\d.]+)\s*(?:U|UNITS?)\s*\)?", re.I)
_SPREAD_RE = re.compile(r"^\s*([A-Z '.&-]+?)\s*([+-]\d+(?:\.\d+)?)", re.I)
_ML_RE     = re.compile(r"^\s*([A-Z '.&-]+?)\s+ML\b", re.I)
_TOTAL_RE  = re.compile(
    r"^\s*([A-Z '.&-]+)\s*/\s*([A-Z '.&-]+)\s+(OVER|UNDER)\s+(\d+(?:\.\d+)?)",
    re.I,
)
_MINOD_RE  = re.compile(r"min[_\s-]?odds[:\s]*([+-]?\d+(?:\.\d+)?)", re.I)


def _code(raw: str) -> str:
    key = raw.upper().strip()
    if key not in TEAM_CODE:
        raise UnmappedTeamError(key)
    return TEAM_CODE[key]


# ── main parser ─────────────────────────────────────────────────────
def parse_tip_email(text: str) -> TipPayload:
    # units (default 1 if absent)
    m_units = _UNITS_RE.search(text)
    units = float(m_units.group(1)) if m_units else 1.0

    # 1️⃣ Totals
    if m := _TOTAL_RE.search(text):
        raw_a, raw_b, over_under, total = m.groups()
        team_a, team_b = _code(raw_a), _code(raw_b)
        return TipPayload(
            units=units,
            team=team_a,
            opponent=team_b,
            kickoff_iso=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            market="TOTAL",
            line=float(total),
            o_u=over_under.upper(),
            min_odds=None,
        )

    # 2️⃣ Spreads
    if m := _SPREAD_RE.search(text):
        raw_team, line_str = m.groups()
        return TipPayload(
            units=units,
            team=_code(raw_team),
            opponent=None,
            kickoff_iso=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            market="SPREAD",
            line=float(line_str),
            o_u=None,
            min_odds=None,
        )

    # 3️⃣ Money-line
    if m := _ML_RE.search(text):
        raw_team = m.group(1)
        min_odds = float(_MINOD_RE.search(text).group(1)) if _MINOD_RE.search(text) else None
        return TipPayload(
            units=units,
            team=_code(raw_team),
            opponent=None,
            kickoff_iso=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            market="ML",
            line=None,
            o_u=None,
            min_odds=min_odds,
        )

    raise ValueError("unrecognised bet format")