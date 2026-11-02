"""
Turns raw price history into the numbers we actually care about:
day-over-day % change, moving average, and volatility.

Nothing in this file touches the LLM - it's all plain, deterministic
math on top of pandas. That's intentional: the numbers in the email
should be trustworthy and easy to double-check by hand if needed.
"""

import pandas as pd

from src.config import settings


def _percent_change(prices: pd.Series) -> float:
    """Change from the second-to-last price to the last price, as a percent."""
    if len(prices) < 2:
        return 0.0
    previous_price = prices.iloc[-2]
    latest_price = prices.iloc[-1]
    return ((latest_price - previous_price) / previous_price) * 100


def _moving_average(prices: pd.Series, window_days: int) -> float:
    """Average closing price over the last `window_days` days."""
    window = prices.tail(window_days)
    return float(window.mean())


def _volatility(prices: pd.Series) -> float:
    """
    Standard deviation of daily returns, as a percent.
    A simple, standard way to express how "jumpy" a stock has been.
    """
    daily_returns = prices.pct_change().dropna()
    if daily_returns.empty:
        return 0.0
    return float(daily_returns.std() * 100)


def calculate_metrics(current_price: float, price_history: pd.Series) -> dict:
    """
    Compute the day-over-day % change, moving average, volatility, and
    flagged status for one ticker, given its current price and recent
    price history.

    This is a plain function, not a generator - it gets called once per
    ticker, as a tool, by the agent. That makes it easy to test on its
    own with made-up numbers (see tests/test_metrics.py).
    """
    pct_change = _percent_change(price_history)
    moving_avg = _moving_average(price_history, settings.moving_average_days)
    volatility = _volatility(price_history)
    flagged = bool(abs(pct_change) >= settings.move_threshold_pct)

    return {
        "price": current_price,
        "pct_change": round(pct_change, 2),
        "moving_avg": round(moving_avg, 2),
        "volatility": round(volatility, 2),
        "flagged": flagged,
    }
