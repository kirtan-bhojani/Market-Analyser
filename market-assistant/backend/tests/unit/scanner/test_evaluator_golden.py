import numpy as np
import pytest

from app.scanner.dsl import parse_rule_definition
from app.scanner.evaluator import compile_rule
from app.scanner.indicators import rel_volume, rsi


def _make_dip_series(base=100.0):
    """40 flat bars, then a sharp 15-bar drop (RSI dives <30) with one volume spike bar."""
    closes = [base] * 40 + list(np.linspace(base, base * 0.7, 15))
    volumes = [20.0] * 55
    volumes[50] = 200.0  # single rel-volume spike, expected trigger bar
    return closes, volumes


# (asset_class, base_price) -- crypto ~100, equity (NSE) ~2900 (INR). The
# dip is scaled proportionally (30% drawdown) so RSI dives <30 at both
# scales; proves the pure rule-evaluation path is asset-class-agnostic.
ASSET_CLASS_CASES = [("crypto", 100.0), ("equity", 2900.0)]


@pytest.mark.parametrize("asset_class,base_price", ASSET_CLASS_CASES)
def test_fires_exactly_at_expected_bar_never_adjacent(asset_class, base_price):
    closes, volumes = _make_dip_series(base=base_price)
    rsi_series = rsi(closes, period=14)
    relvol_series = rel_volume(volumes, period=20)

    definition = {
        "all": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    }
    compiled = compile_rule(parse_rule_definition(definition))

    fired_bars = []
    for i in range(len(closes)):
        snapshot = {"5m": {"rsi:14": rsi_series[i], "rel_volume:20": relvol_series[i]}}
        if compiled.evaluate(snapshot):
            fired_bars.append(i)

    assert fired_bars == [50]
    assert 49 not in fired_bars
    assert 51 not in fired_bars


def test_any_combinator_fires_when_one_branch_true():
    definition = {
        "any": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 10},   # never true
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    }
    compiled = compile_rule(parse_rule_definition(definition))
    assert compiled.evaluate({"5m": {"rsi:14": 50, "rel_volume:20": 5}}) is True
    assert compiled.evaluate({"5m": {"rsi:14": 50, "rel_volume:20": 1}}) is False


def test_required_indicators_lists_each_ind_tf_pair_once():
    definition = {
        "all": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
            {"ind": "rsi", "tf": "5m", "op": ">", "value": 5},
            {"ind": "rel_volume", "tf": "15m", "op": ">", "value": 2},
        ]
    }
    compiled = compile_rule(parse_rule_definition(definition))
    assert sorted(compiled.required_indicators()) == sorted(
        [("rsi:14", "5m"), ("rel_volume:20", "15m")]
    )


def test_missing_indicator_in_snapshot_evaluates_false_not_exception():
    definition = {"ind": "rsi", "tf": "5m", "op": "<", "value": 30}
    compiled = compile_rule(parse_rule_definition(definition))
    assert compiled.evaluate({"5m": {}}) is False
    assert compiled.evaluate({}) is False
