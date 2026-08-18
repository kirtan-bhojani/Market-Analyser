import math
from typing import TypedDict

import pandas as pd


class CorrelationMatrix(TypedDict):
    symbols: list[str]
    matrix: list[list[float | None]]


def compute_correlation_matrix(
    returns_by_symbol: dict[str, pd.Series],
) -> CorrelationMatrix:
    symbols = list(returns_by_symbol.keys())
    # Align on the timestamp INDEX, never by position: instruments have
    # different histories/gaps, so pairing the i-th bar of each series
    # correlates unrelated points. Building the frame from the ts-indexed
    # series unions on timestamp; corr() then uses pairwise-complete overlap.
    frame = pd.DataFrame(returns_by_symbol)
    corr = frame.corr(method="pearson")

    def _cell(row: str, col: str) -> float | None:
        # A pair with no overlapping timestamps yields NaN, which is not valid
        # JSON and would crash the frontend's toFixed(). Emit null instead.
        value = float(corr.loc[row, col])
        return None if math.isnan(value) else round(value, 6)

    matrix = [[_cell(row, col) for col in symbols] for row in symbols]
    return {"symbols": symbols, "matrix": matrix}
