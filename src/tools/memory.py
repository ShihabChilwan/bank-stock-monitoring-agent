"""
The agent's persistent memory.

Three tables, each with one job:
  - daily_metrics: what the agent fetched/computed
  - insights:      what the agent said (LLM output)
  - email_log:     what the agent sent, and when

This is what lets the agent remember yesterday's insight, avoid sending
a duplicate automatic email on the same day, and give a demo-able history
of everything it has done.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path

from src.config import settings


def _connect() -> sqlite3.Connection:
    """Open a connection to the SQLite file, creating the folder if needed."""
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db() -> None:
    """Create all tables if they don't already exist. Safe to call every run."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                price REAL,
                pct_change REAL,
                moving_avg REAL,
                volatility REAL,
                flagged BOOLEAN
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                insight_text TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                status TEXT NOT NULL,
                trigger_type TEXT NOT NULL
            )
            """
        )


def save_daily_metrics(ticker: str, metrics: dict) -> None:
    """Store today's computed metrics for one ticker."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO daily_metrics (ticker, date, price, pct_change, moving_avg, volatility, flagged)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                date.today().isoformat(),
                metrics["price"],
                metrics["pct_change"],
                metrics["moving_avg"],
                metrics["volatility"],
                metrics["flagged"],
            ),
        )


def save_insight(ticker: str, insight_text: str) -> None:
    """Store today's LLM-generated insight for one ticker."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO insights (ticker, date, insight_text) VALUES (?, ?, ?)",
            (ticker, date.today().isoformat(), insight_text),
        )


def get_last_insight(ticker: str) -> str | None:
    """
    Return the most recent insight text saved for a ticker (from any
    previous day), or None if we've never generated one before.
    This is what lets the LLM say things like "compared to yesterday...".
    """
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT insight_text FROM insights
            WHERE ticker = ?
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()
    return row[0] if row else None


def was_scheduled_email_sent_today() -> bool:
    """
    True if an automatic (cron-triggered) email has already gone out today.
    Used to avoid sending a duplicate if the scheduled job somehow runs twice.
    Manual resends are not affected by this check.
    """
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM email_log
            WHERE date = ? AND trigger_type = 'scheduled' AND status = 'sent'
            LIMIT 1
            """,
            (date.today().isoformat(),),
        ).fetchone()
    return row is not None


def log_email_sent(trigger_type: str, status: str = "sent") -> None:
    """Record that an email was sent (or that sending failed)."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO email_log (date, sent_at, status, trigger_type)
            VALUES (?, ?, ?, ?)
            """,
            (date.today().isoformat(), datetime.now().isoformat(timespec="seconds"), status, trigger_type),
        )


def get_latest_snapshot() -> dict:
    """
    Return today's metrics and insight for every ticker that has been
    processed so far today. Used by the Streamlit dashboard to show what
    the agent just did, since the agent's own reply is free-form text
    rather than structured data.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT daily_metrics.ticker,
                   daily_metrics.price,
                   daily_metrics.pct_change,
                   daily_metrics.moving_avg,
                   daily_metrics.volatility,
                   daily_metrics.flagged,
                   insights.insight_text
            FROM daily_metrics
            LEFT JOIN insights
                ON daily_metrics.ticker = insights.ticker
                AND daily_metrics.date = insights.date
            WHERE daily_metrics.date = ?
            """,
            (date.today().isoformat(),),
        ).fetchall()

    return {
        row[0]: {
            "price": row[1],
            "pct_change": row[2],
            "moving_avg": row[3],
            "volatility": row[4],
            "flagged": bool(row[5]),
            "insight": row[6],
        }
        for row in rows
    }


def get_email_history(limit: int = 20) -> list[tuple]:
    """Return the most recent email log entries, newest first. Used by the Streamlit dashboard."""
    with _connect() as conn:
        return conn.execute(
            "SELECT date, sent_at, status, trigger_type FROM email_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
