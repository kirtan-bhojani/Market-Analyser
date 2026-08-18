import pandas as pd

RSI_WINDOW = 14
VOL_WINDOW = 10
VOLUME_Z_WINDOW = 20
VWAP_WINDOW = 20
LAG_PERIODS = (1, 3, 5)
REGIME_CATEGORIES = ("trend_up", "trend_down", "range", "high_vol")


def _rsi(close: pd.Series, window: int = RSI_WINDOW) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Flat runs (avg_loss == 0) => RS is inf => RSI correctly saturates at 100;
    # replace the resulting +/-inf from 0/0 with a neutral 50.
    return (
        rsi.replace([float("inf"), float("-inf")], 100.0)
        .fillna(50.0)
        .where(avg_gain.notna(), other=float("nan"))
    )


def build_features(candles: pd.DataFrame, regime: pd.Series | None = None) -> pd.DataFrame:
    close = candles["c"]
    volume = candles["v"]
    typical_price = (candles["h"] + candles["l"] + candles["c"]) / 3.0

    features = pd.DataFrame(index=candles.index)
    for lag in LAG_PERIODS:
        features[f"ret_{lag}"] = close.pct_change(lag)

    returns_1 = close.pct_change(1)
    features["vol_10"] = returns_1.rolling(VOL_WINDOW).std()
    features["rsi_14"] = _rsi(close)

    vol_mean = volume.rolling(VOLUME_Z_WINDOW).mean()
    vol_std = volume.rolling(VOLUME_Z_WINDOW).std()
    volume_z = (volume - vol_mean) / vol_std
    # Flat-volume window: std == 0 -> 0/0 = NaN. The bar is valid (no volume
    # anomaly), so treat the z-score as 0 rather than letting dropna() discard
    # it — which could drop the just-closed bar and break serve-time iloc[-1].
    # (vol_std is NaN during warm-up, where `== 0` is False, so warm-up rows
    # stay NaN and are correctly dropped.)
    features["volume_z"] = volume_z.mask(vol_std == 0, 0.0)

    vol_sum = volume.rolling(VWAP_WINDOW).sum()
    vwap = (typical_price * volume).rolling(VWAP_WINDOW).sum() / vol_sum
    vwap_dist = (close - vwap) / vwap
    # All-zero-volume window: vwap is undefined (0/0) or the ratio divides by a
    # zero vwap -> inf. Treat distance-from-VWAP as 0 rather than dropping the
    # bar. Warm-up (vol_sum NaN) stays NaN and is dropped as before.
    vwap_dist = vwap_dist.replace([float("inf"), float("-inf")], 0.0)
    features["vwap_dist"] = vwap_dist.mask(vol_sum == 0, 0.0)

    if regime is not None:
        aligned = regime.reindex(candles.index)
        for category in REGIME_CATEGORIES:
            features[f"regime_{category}"] = (aligned == category).astype(float)
    else:
        for category in REGIME_CATEGORIES:
            features[f"regime_{category}"] = 0.0

    features = features.dropna()
    features["feature_ts"] = features.index
    return features
