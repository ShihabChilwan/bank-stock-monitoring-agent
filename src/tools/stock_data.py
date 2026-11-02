"""
Tools for fetching stock price data from Yahoo Finance (via yfinance).

This is the only file that talks to the outside world for price data, so
it's also the only place that needs retry logic for flaky network calls.
"""

import functools
import time

import pandas as pd
import yfinance as yf


def retry(max_attempts: int = 3, delay_seconds: float = 2.0):
    """
    A small decorator that re-runs a function if it raises an exception,
    waiting a bit between attempts. Used here because yfinance calls
    occasionally fail due to network hiccups, not because of a real bug.

    If every attempt fails, the last exception is raised so the caller
    (main.py or the LangGraph node) can decide how to handle it.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as error:  # noqa: BLE001 - we want to retry on anything
                    last_error = error
                    print(
                        f"[stock_data] {func.__name__} failed on attempt "
                        f"{attempt}/{max_attempts}: {error}"
                    )
                    if attempt < max_attempts:
                        time.sleep(delay_seconds)
            raise last_error

        return wrapper

    return decorator


@retry(max_attempts=3)
def fetch_current_price(ticker: str) -> float:
    """Return the most recent closing price available for a ticker."""
    history = yf.Ticker(ticker).history(period="1d")
    if history.empty:
        raise ValueError(f"No price data returned for ticker '{ticker}'.")
    return float(history["Close"].iloc[-1])


@retry(max_attempts=3)
def fetch_historical_prices(ticker: str, days: int) -> pd.Series:
    """
    Return a pandas Series of closing prices for the last `days` calendar
    days, indexed by date. Used to compute % change, moving average, and
    volatility for a ticker.
    """
    history = yf.Ticker(ticker).history(period=f"{days}d")
    if history.empty:
        raise ValueError(f"No historical data returned for ticker '{ticker}'.")
    return history["Close"]


def fetch_all_tickers(tickers: list[str], history_days: int) -> dict:
    """
    Fetch current price + historical prices for every ticker in the list.

    If one ticker fails after all retries, it is skipped (with a printed
    warning) instead of crashing the whole run - the rest of the tickers
    should still get processed.
    """
    results = {}
    for ticker in tickers:
        try:
            results[ticker] = {
                "current_price": fetch_current_price(ticker),
                "history": fetch_historical_prices(ticker, history_days),
            }
        except Exception as error:  # noqa: BLE001 - deliberately broad, see docstring
            print(f"[stock_data] Skipping '{ticker}' after repeated failures: {error}")
    return results
