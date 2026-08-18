import pandas as pd


def build_fixed_horizon_labels(candles: pd.DataFrame, horizon: int) -> pd.DataFrame:
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    close = candles["c"]
    future_close = close.shift(-horizon)
    y = (future_close > close).astype(float)

    label_ts = pd.Series(candles.index, index=candles.index).shift(-horizon)

    df = pd.DataFrame({"label_ts": label_ts, "y": y}, index=candles.index)
    return df.dropna()


def build_triple_barrier_labels(
    candles: pd.DataFrame, horizon: int, tp_pct: float, sl_pct: float
) -> pd.DataFrame:
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    close = candles["c"]
    high = candles["h"]
    low = candles["l"]
    n = len(candles)

    rows_ts = []
    labels = []
    label_ts_list = []

    for i in range(n - horizon):
        entry = close.iloc[i]
        tp_level = entry * (1 + tp_pct)
        sl_level = entry * (1 - sl_pct)

        window_high = high.iloc[i + 1 : i + 1 + horizon]
        window_low = low.iloc[i + 1 : i + 1 + horizon]

        y = None
        touch_ts = None
        for j in range(len(window_high)):
            hit_tp = window_high.iloc[j] >= tp_level
            hit_sl = window_low.iloc[j] <= sl_level
            if hit_tp and hit_sl:
                y, touch_ts = (
                    0.0,
                    window_high.index[j],
                )  # ambiguous same-bar touch: conservative loss
                break
            if hit_tp:
                y, touch_ts = 1.0, window_high.index[j]
                break
            if hit_sl:
                y, touch_ts = 0.0, window_low.index[j]
                break

        if y is None:
            # No barrier touched within the horizon: fall back to the sign
            # of the final close vs. entry (standard triple-barrier convention).
            final_close = close.iloc[i + horizon]
            y = 1.0 if final_close > entry else 0.0
            touch_ts = candles.index[i + horizon]

        rows_ts.append(candles.index[i])
        labels.append(y)
        label_ts_list.append(touch_ts)

    return pd.DataFrame({"label_ts": label_ts_list, "y": labels}, index=rows_ts)
