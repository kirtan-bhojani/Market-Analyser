"""Grounding guard: flag numeric *market-fact* claims in an answer that are not
backed by this turn's tool outputs. The orchestrator regenerates once on
failure, then substitutes ``FALLBACK_MESSAGE``.

Only price/indicator-value-shaped numbers count as claims: a decimal
(``62.4``, ``65000.0``), a 5+ digit number (a price like ``71234``), or a
``$``-prefixed / magnitude-suffixed number. Bare shorter integers (indicator
periods ``9/21/14``, scale refs ``0-100``, 4-digit years/counts like ``2024``)
are treated as prose, not verifiable facts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.schemas.chat import ToolResult

FALLBACK_MESSAGE = "I don't have that data."

# A number token bounded by non-alphanumerics (so "1h"/"1m"/"BTC" are excluded).
# Captures: optional leading $, the numeric core (plain/comma OR space-grouped
# thousands, optional decimal), and an optional magnitude suffix (k/m/b) — so
# "65k" and "71 234" are recognised as claims, not silently ignored.
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9.])(\$?)((?:\d{1,3}(?: \d{3})+|\d[\d,]*)(?:\.\d+)?)([kKmMbB]?)(?![A-Za-z0-9.])"
)
_TOLERANCE = 0.05
# Relative slack so large prices (e.g. 65000) aren't rejected over sub-dollar
# rounding while small indicator values keep the tight absolute floor.
_REL_TOLERANCE = 0.001
_SUFFIX_MULT = {"k": 1e3, "m": 1e6, "b": 1e9}

# Keys whose numeric values are identifiers/pagination, never market facts — a
# claim must not be grounded by coincidentally equalling one of these.
_NON_FACT_KEYS = {
    "id", "ids", "count", "index", "idx", "page", "limit", "offset", "rank",
    "n", "size", "instrument_id", "rule_id", "user_id", "model_id", "session_id",
}


@dataclass
class GroundingResult:
    grounded: bool
    unsupported_claims: list[str]


def _collect(obj: Any, numbers: list[float]) -> None:
    # T2-15: harvest known numbers from SCALAR fields only. Arrays (e.g. a list
    # of closes) would otherwise let a claim be "grounded" by coincidentally
    # matching any one of many series values, so lists are skipped entirely.
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _NON_FACT_KEYS:
                continue
            _collect(value, numbers)
    elif isinstance(obj, list):
        return
    elif isinstance(obj, bool):
        return
    elif isinstance(obj, int | float):
        numbers.append(float(obj))


def _known_numbers(facts: list[ToolResult]) -> list[float]:
    numbers: list[float] = []
    for fact in facts:
        if not fact.ok or not fact.data:
            continue
        _collect(fact.data, numbers)
    return numbers


def _is_market_fact_claim(dollar: str, core: str, suffix: str) -> bool:
    # Needs a currency ($), magnitude suffix (k/m/b), or decimal to count as a
    # price/indicator claim. A BARE integer must be 5+ digits — a 4-digit bare
    # number is almost always a year ("2024") or a count, not a verifiable price,
    # and flagging it caused false ungrounded fallbacks.
    if dollar == "$" or suffix:
        return True
    if "." in core:
        return True
    return len(core.replace(",", "").replace(" ", "")) >= 5


def _claim_value(core: str, suffix: str) -> float:
    base = float(core.replace(",", "").replace(" ", ""))
    return base * _SUFFIX_MULT.get(suffix.lower(), 1.0)


def check_grounding(answer: str, facts: list[ToolResult]) -> GroundingResult:
    known = _known_numbers(facts)
    unsupported: list[str] = []
    for dollar, core, suffix in _NUMBER_RE.findall(answer):
        if not _is_market_fact_claim(dollar, core, suffix):
            continue
        try:
            claim = _claim_value(core, suffix)
        except ValueError:
            continue
        if not any(
            abs(claim - k) <= max(_TOLERANCE, _REL_TOLERANCE * abs(k)) for k in known
        ):
            unsupported.append(f"{dollar}{core}{suffix}")
    return GroundingResult(grounded=len(unsupported) == 0, unsupported_claims=unsupported)
