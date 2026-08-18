import pandas as pd

from app.ml.labels import build_fixed_horizon_labels, build_triple_barrier_labels


def test_fixed_horizon_labels_match_hand_built_fixture():
    idx = pd.date_range("2024-01-01", periods=6, freq="1h", tz="UTC")
    candles = pd.DataFrame({"c": [100.0, 101.0, 99.0, 105.0, 103.0, 110.0]}, index=idx)
    labels = build_fixed_horizon_labels(candles, horizon=2)

    # row0: close[0]=100 -> close[2]=99  -> down -> y=0, label_ts=idx[2]
    # row1: close[1]=101 -> close[3]=105 -> up   -> y=1, label_ts=idx[3]
    # row2: close[2]=99  -> close[4]=103 -> up   -> y=1, label_ts=idx[4]
    # row3: close[3]=105 -> close[5]=110 -> up   -> y=1, label_ts=idx[5]
    # rows 4,5 have no future bar at +2 -> dropped
    assert len(labels) == 4
    assert list(labels["y"]) == [0.0, 1.0, 1.0, 1.0]
    assert list(labels["label_ts"]) == [idx[2], idx[3], idx[4], idx[5]]
    assert list(labels.index) == [idx[0], idx[1], idx[2], idx[3]]


def test_triple_barrier_labels_match_hand_built_fixture():
    idx = pd.date_range("2024-01-01", periods=7, freq="1h", tz="UTC")
    candles = pd.DataFrame(
        {
            "c": [100.0, 100.2, 103.0, 110.0, 108.7, 111.0, 112.0],
            "h": [100.0, 100.5, 103.0, 110.0, 109.0, 112.0, 113.0],
            "l": [100.0, 99.5, 100.0, 110.0, 108.5, 110.0, 111.0],
        },
        index=idx,
    )
    # Row at i=0: entry=100, tp=102 (2%), sl=99 (1%). Window = idx[1], idx[2].
    #   idx[1]: h=100.5 (<102), l=99.5 (>99)      -> no touch
    #   idx[2]: h=103.0 (>=102)                    -> TP hit -> y=1, touch at idx[2]
    # Row at i=3: entry=110, tp=112.2, sl=108.9. Window = idx[4], idx[5].
    #   idx[4]: h=109.0 (<112.2), l=108.5 (<=108.9) -> SL hit -> y=0, touch at idx[4]
    labels = build_triple_barrier_labels(candles, horizon=2, tp_pct=0.02, sl_pct=0.01)

    row0 = labels.loc[idx[0]]
    assert row0["y"] == 1.0
    assert row0["label_ts"] == idx[2]

    row3 = labels.loc[idx[3]]
    assert row3["y"] == 0.0
    assert row3["label_ts"] == idx[4]
