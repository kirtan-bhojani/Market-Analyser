import pytest

from app.strategies.registry import get_strategy, list_strategies, register


class DummyStrategy:
    name = "dummy"
    regime_mode = "any"

    def param_schema(self):
        return {"type": "object", "properties": {}, "required": []}

    def default_params(self):
        return {}

    def generate_signals(self, candles, params):
        return []


def test_register_and_get():
    register(DummyStrategy())
    assert get_strategy("dummy").name == "dummy"


def test_unknown_strategy_raises_keyerror():
    with pytest.raises(KeyError):
        get_strategy("does_not_exist")


def test_list_strategies_contains_registered():
    register(DummyStrategy())
    names = [s.name for s in list_strategies()]
    assert "dummy" in names
