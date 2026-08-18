"""Compile parsed rule DSL trees into evaluable predicates.

`compile_rule` turns a `RuleNode` tree (from `app.scanner.dsl`) into a
`CompiledRule` whose `evaluate` runs against a per-timeframe indicator
snapshot. Conditions are looked up by BARE indicator name (e.g. ``"rsi"``);
a missing key or a NaN value evaluates to False (never raises). Callers that
hold period-suffixed cache keys (Task 7 worker) are responsible for adapting
them to this bare-name snapshot shape before calling `evaluate`.
"""

from __future__ import annotations

import math
import operator
from collections.abc import Callable

from app.scanner.dsl import AllNode, AnyNode, Condition, RuleNode

OPS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


class CompiledRule:
    def __init__(self, node: RuleNode) -> None:
        self._node = node

    def evaluate(self, snapshot_by_tf: dict[str, dict[str, float]]) -> bool:
        return self._eval_node(self._node, snapshot_by_tf)

    def _eval_node(self, node: RuleNode, snapshot_by_tf: dict[str, dict[str, float]]) -> bool:
        if isinstance(node, AllNode):
            return all(self._eval_node(child, snapshot_by_tf) for child in node.all)
        if isinstance(node, AnyNode):
            return any(self._eval_node(child, snapshot_by_tf) for child in node.any)
        if isinstance(node, Condition):
            tf_values = snapshot_by_tf.get(node.tf, {})
            value = tf_values.get(node.key)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return False
            return OPS[node.op](value, node.value)
        raise TypeError(f"unknown node type {type(node)!r}")

    def required_indicators(self) -> list[tuple[str, str]]:
        seen: set[tuple[str, str]] = set()
        self._collect(self._node, seen)
        return list(seen)

    def _collect(self, node: RuleNode, seen: set[tuple[str, str]]) -> None:
        if isinstance(node, AllNode):
            for child in node.all:
                self._collect(child, seen)
        elif isinstance(node, AnyNode):
            for child in node.any:
                self._collect(child, seen)
        elif isinstance(node, Condition):
            seen.add((node.key, node.tf))


def compile_rule(node: RuleNode) -> CompiledRule:
    return CompiledRule(node)
