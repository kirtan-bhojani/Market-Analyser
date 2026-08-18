VALID_CLOSED_KLINE = {
    "e": "kline",
    "E": 1700000060000,
    "s": "BTCUSDT",
    "k": {
        "t": 1700000000000,
        "T": 1700000059999,
        "s": "BTCUSDT",
        "i": "1m",
        "o": "35000.10",
        "c": "35010.50",
        "h": "35020.00",
        "l": "34990.00",
        "v": "12.34500000",
        "x": True,
    },
}

UNCLOSED_KLINE = {
    **VALID_CLOSED_KLINE,
    "k": {**VALID_CLOSED_KLINE["k"], "x": False},
}

MISSING_FIELD_KLINE = {
    "e": "kline",
    "E": 1700000060000,
    "s": "BTCUSDT",
    "k": {
        "t": 1700000000000,
        "T": 1700000059999,
        "s": "BTCUSDT",
        "i": "1m",
        "o": "35000.10",
        "c": "35010.50",
        "h": "35020.00",
        # "l" missing
        "v": "12.34500000",
        "x": True,
    },
}

NON_NUMERIC_KLINE = {
    **VALID_CLOSED_KLINE,
    "k": {**VALID_CLOSED_KLINE["k"], "o": "not-a-number"},
}

WRONG_EVENT_TYPE = {**VALID_CLOSED_KLINE, "e": "trade"}
