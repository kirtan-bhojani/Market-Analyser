from app.chat.guards.grounding import FALLBACK_MESSAGE, check_grounding
from app.schemas.chat import ToolResult


def _facts():
    return [
        ToolResult(
            name="get_indicators",
            ok=True,
            data={
                "symbol": "BTC/USDT",
                "tf": "1h",
                "rsi": 62.4,
                "ema_9": 65120.0,
                "ema_21": 64890.0,
                "vwap": 65000.0,
                "atr": 320.5,
                "adx": 28.1,
            },
        )
    ]


def test_answer_citing_tool_numbers_passes():
    answer = "BTC/USDT on 1h has RSI 62.4 and is trading above VWAP at 65000.0."
    result = check_grounding(answer, _facts())
    assert result.grounded is True
    assert result.unsupported_claims == []


def test_answer_with_fabricated_price_is_flagged():
    answer = "BTC is currently at $71234.56, a strong breakout level."
    result = check_grounding(answer, _facts())
    assert result.grounded is False
    assert any("71234.56" in c for c in result.unsupported_claims)


def test_answer_with_no_numeric_claims_passes():
    answer = "Momentum indicators generally measure the speed of price change."
    result = check_grounding(answer, _facts())
    assert result.grounded is True


def test_indicator_period_labels_are_not_flagged():
    answer = "An EMA(9/21) crossover on the 1h with RSI 62.4 suggests trend continuation."
    result = check_grounding(answer, _facts())
    assert result.grounded is True


def test_fallback_message_constant():
    assert FALLBACK_MESSAGE == "I don't have that data."
