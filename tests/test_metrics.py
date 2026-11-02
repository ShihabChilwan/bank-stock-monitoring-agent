"""
Basic unit tests for src/tools/metrics.py, using synthetic price data
instead of live yfinance calls so the tests run offline and fast.
"""

import pandas as pd

from src.tools.metrics import calculate_metrics


def test_calculate_metrics_basic_case():
    # A simple, steadily rising price series: 100 -> 101 -> ... -> 107
    prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107], dtype=float)

    metrics = calculate_metrics(current_price=107.0, price_history=prices)

    # Day-over-day change from 106 to 107 is about +0.94%
    assert round(metrics["pct_change"], 2) == round(((107 - 106) / 106) * 100, 2)

    # Moving average should be a sensible number in the middle of the range
    assert metrics["moving_avg"] > 100

    # A steady 1-point-per-day rise is not a big move, so it should not be flagged
    assert metrics["flagged"] is False


def test_calculate_metrics_flags_large_move():
    # A sudden 10% jump on the last day
    prices = pd.Series([100, 100, 100, 100, 100, 100, 100, 110], dtype=float)

    metrics = calculate_metrics(current_price=110.0, price_history=prices)

    assert metrics["pct_change"] == 10.0
    assert metrics["flagged"] is True
