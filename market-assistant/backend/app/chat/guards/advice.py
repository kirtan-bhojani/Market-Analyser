"""Advice guard: enforce educational framing — no imperative buy/sell or
guarantee language, and (optionally) require the disclaimer on recommendation
answers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DISCLAIMER_TEXT = "Educational analysis. Not investment advice. Past performance ≠ future results."

# Kept as literal substrings so their violation labels stay stable for callers.
_FORBIDDEN_PHRASES = [
    "you should buy",
    "you should sell",
    "guaranteed",
    "buy now",
    "sell now",
    "guaranteed to go up",
    "guaranteed to go down",
]

# Broadened coverage beyond the seven literals: imperative trade directives and
# guarantee/certainty language in any phrasing. Conservative by design — a match
# routes the answer to the educational fallback.
_FORBIDDEN_PATTERNS = [
    re.compile(p)
    for p in [
        r"\byou (should|must|need to|have to|ought to|gotta) "
        r"(?:\w+ly )*"  # allow adverbs between the modal and the verb ("definitely buy")
        r"(buy|sell|short|long|hold|dump|exit|enter|invest|ape)\b",
        r"\b(buy|sell|short|long|dump)\s+[\w/$]+\s+(now|today|immediately|asap)\b",
        r"\b(buy|sell|short|long)\s+(now|today|immediately|asap)\b",
        r"\bguarantee(d|s)?\b",
        r"\brisk[-\s]?free\b",
        r"\bcan'?t lose\b",
        r"\bsure thing\b",
        r"\bwill (definitely|certainly|surely|absolutely|100%?) "
        r"(moon|rise|fall|go up|go down|double|triple|pump|dump|profit)\b",
        r"\b(guaranteed|definite|certain|100%?) (profit|gain|return|win|money)\b",
    ]
]


@dataclass
class AdviceResult:
    ok: bool
    violations: list[str]


def check_advice_language(answer: str, requires_disclaimer: bool = False) -> AdviceResult:
    lowered = answer.lower()
    violations = [phrase for phrase in _FORBIDDEN_PHRASES if phrase in lowered]
    for pattern in _FORBIDDEN_PATTERNS:
        match = pattern.search(lowered)
        if match and match.group(0) not in violations:
            violations.append(match.group(0))
    if requires_disclaimer and DISCLAIMER_TEXT.lower() not in lowered:
        violations.append("missing disclaimer")
    return AdviceResult(ok=len(violations) == 0, violations=violations)
