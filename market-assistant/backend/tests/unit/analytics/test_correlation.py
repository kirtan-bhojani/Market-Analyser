import pandas as pd

from app.analytics.correlation import compute_correlation_matrix


def test_identical_series_correlate_to_one():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = compute_correlation_matrix({"A": s, "B": s.copy()})
    assert result["symbols"] == ["A", "B"]
    assert result["matrix"][0][1] == 1.0
    assert result["matrix"][1][0] == 1.0


def test_inverse_series_correlate_to_negative_one():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    inv = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
    result = compute_correlation_matrix({"A": s, "B": inv})
    assert result["matrix"][0][1] == -1.0


def test_diagonal_is_one_and_matrix_square_symmetric():
    a = pd.Series([1.0, 2.0, 1.5, 3.0, 2.5])
    b = pd.Series([2.0, 1.0, 2.5, 1.5, 3.0])
    c = pd.Series([1.0, 3.0, 2.0, 4.0, 1.0])
    result = compute_correlation_matrix({"A": a, "B": b, "C": c})
    m = result["matrix"]
    n = len(result["symbols"])
    assert n == 3
    assert all(len(row) == n for row in m)
    for i in range(n):
        assert m[i][i] == 1.0
    for i in range(n):
        for j in range(n):
            assert m[i][j] == m[j][i]
