import pytest

from app.scanner.dsl import AllNode, AnyNode, Condition, RuleDSLError, parse_rule_definition

VALID_DEFINITION = {
    "all": [
        {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
        {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
    ]
}


def test_parses_all_combinator_with_two_conditions():
    node = parse_rule_definition(VALID_DEFINITION)
    assert isinstance(node, AllNode)
    assert len(node.all) == 2
    assert isinstance(node.all[0], Condition)
    assert node.all[0] == Condition(ind="rsi", tf="5m", op="<", value=30, params={})
    assert node.all[1] == Condition(ind="rel_volume", tf="5m", op=">", value=2, params={})


def test_parses_nested_any_inside_all():
    definition = {
        "all": [
            {
                "any": [
                    {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
                    {"ind": "rsi", "tf": "15m", "op": "<", "value": 25},
                ]
            },
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    }
    node = parse_rule_definition(definition)
    assert isinstance(node, AllNode)
    assert isinstance(node.all[0], AnyNode)
    assert len(node.all[0].any) == 2


def test_condition_accepts_optional_params():
    definition = {"ind": "ema", "tf": "1h", "op": ">", "value": 100, "params": {"period": 21}}
    node = parse_rule_definition(definition)
    assert node == Condition(ind="ema", tf="1h", op=">", value=100, params={"period": 21})


@pytest.mark.parametrize(
    "bad_definition,expected_path",
    [
        ({}, "$"),
        ({"all": []}, "$.all"),
        ({"all": [{"ind": "rsi", "tf": "5m", "op": "<"}]}, "$.all[0].value"),
        ({"ind": "unknown_indicator", "tf": "5m", "op": "<", "value": 30}, "$.ind"),
        ({"ind": "rsi", "tf": "3m", "op": "<", "value": 30}, "$.tf"),
        ({"ind": "rsi", "tf": "5m", "op": "??", "value": 30}, "$.op"),
        ({"ind": "rsi", "tf": "5m", "op": "<", "value": "not-a-number"}, "$.value"),
    ],
)
def test_invalid_definitions_raise_typed_error(bad_definition, expected_path):
    with pytest.raises(RuleDSLError) as exc_info:
        parse_rule_definition(bad_definition)
    assert exc_info.value.path == expected_path
