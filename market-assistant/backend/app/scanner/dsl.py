"""Rule DSL parser and validation for the scanner rule engine.

Parses a raw (JSON-decoded) rule definition into a typed `RuleNode` tree,
raising `RuleDSLError` with a JSONPath-like `path` pointing at the offending
field on any validation failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_INDICATORS = {"rsi", "ema", "sma", "vwap", "atr", "adx", "rel_volume", "gap_pct"}
VALID_TFS = {"1m", "5m", "15m", "1h", "1d"}
VALID_OPS = {"<", "<=", ">", ">=", "==", "!="}

# Default lookback for period-based indicators; vwap/gap_pct take no period.
DEFAULT_PERIODS = {"rsi": 14, "ema": 21, "sma": 20, "atr": 14, "adx": 14, "rel_volume": 20}


class RuleDSLError(ValueError):
    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


@dataclass(frozen=True)
class Condition:
    ind: str
    tf: str
    op: str
    value: float
    params: dict[str, float] = field(default_factory=dict)

    @property
    def period(self) -> int | None:
        """Resolved lookback: params['period'] if set, else the indicator default;
        None for indicators that take no period (vwap, gap_pct)."""
        if self.ind not in DEFAULT_PERIODS:
            return None
        return int(self.params.get("period", DEFAULT_PERIODS[self.ind]))

    @property
    def key(self) -> str:
        """Period-suffixed indicator key (``rsi:14``, ``vwap``) used both as the
        cache request key and the snapshot lookup key, so a custom period is
        honored rather than collapsing to a bare name."""
        p = self.period
        return self.ind if p is None else f"{self.ind}:{p}"


@dataclass(frozen=True)
class AllNode:
    all: list[RuleNode]


@dataclass(frozen=True)
class AnyNode:
    any: list[RuleNode]


RuleNode = Condition | AllNode | AnyNode


def _parse_condition(raw: dict[str, Any], path: str) -> Condition:
    ind = raw.get("ind")
    if ind not in VALID_INDICATORS:
        raise RuleDSLError(f"{path}.ind", f"unknown indicator {ind!r}")
    tf = raw.get("tf")
    if tf not in VALID_TFS:
        raise RuleDSLError(f"{path}.tf", f"unknown timeframe {tf!r}")
    op = raw.get("op")
    if op not in VALID_OPS:
        raise RuleDSLError(f"{path}.op", f"unknown operator {op!r}")
    if "value" not in raw:
        raise RuleDSLError(f"{path}.value", "missing required field 'value'")
    value = raw["value"]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise RuleDSLError(f"{path}.value", f"value must be numeric, got {value!r}")
    params = raw.get("params", {})
    if not isinstance(params, dict):
        raise RuleDSLError(f"{path}.params", "params must be an object")
    if "period" in params:
        period = params["period"]
        if (
            isinstance(period, bool)
            or not isinstance(period, (int, float))
            or int(period) != period
            or int(period) < 1
        ):
            raise RuleDSLError(f"{path}.params.period", "period must be a positive integer")
        if ind not in DEFAULT_PERIODS:
            raise RuleDSLError(f"{path}.params.period", f"{ind!r} takes no period")
    return Condition(ind=ind, tf=tf, op=op, value=float(value), params=params)


def _parse_node(raw: Any, path: str) -> RuleNode:
    if not isinstance(raw, dict):
        raise RuleDSLError(path, "node must be an object")
    if "all" in raw:
        children = raw["all"]
        if not isinstance(children, list) or len(children) == 0:
            raise RuleDSLError(f"{path}.all", "'all' must be a non-empty list")
        return AllNode(all=[_parse_node(c, f"{path}.all[{i}]") for i, c in enumerate(children)])
    if "any" in raw:
        children = raw["any"]
        if not isinstance(children, list) or len(children) == 0:
            raise RuleDSLError(f"{path}.any", "'any' must be a non-empty list")
        return AnyNode(any=[_parse_node(c, f"{path}.any[{i}]") for i, c in enumerate(children)])
    if "ind" in raw:
        return _parse_condition(raw, path)
    raise RuleDSLError(path, "node must contain 'all', 'any', or 'ind'")


def parse_rule_definition(raw: dict[str, Any]) -> RuleNode:
    return _parse_node(raw, "$")
