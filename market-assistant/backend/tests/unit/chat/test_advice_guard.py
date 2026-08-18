from app.chat.guards.advice import DISCLAIMER_TEXT, check_advice_language


def test_imperative_buy_phrase_flagged():
    answer = "You should buy DOGE right now, it's guaranteed to go up."
    result = check_advice_language(answer)
    assert result.ok is False
    lowered = [v.lower() for v in result.violations]
    assert "you should buy" in lowered
    assert "guaranteed" in lowered


def test_educational_framing_with_disclaimer_passes():
    answer = (
        "Setup detected: DOGE is showing high volatility with RSI at 78, historically "
        "overextended moves like this see mean reversion. Key risks: momentum can persist "
        "longer than expected and liquidity is thinner than majors. "
        f"{DISCLAIMER_TEXT}"
    )
    result = check_advice_language(answer)
    assert result.ok is True
    assert result.violations == []


def test_missing_disclaimer_on_recommendation_flagged():
    answer = "DOGE looks overextended based on RSI. Consider the risks before acting."
    result = check_advice_language(answer, requires_disclaimer=True)
    assert result.ok is False
    assert "missing disclaimer" in [v.lower() for v in result.violations]
