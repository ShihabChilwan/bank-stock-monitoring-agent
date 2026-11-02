"""
Central place for all project settings.

Every other module reads its configuration from here instead of calling
os.getenv() directly. That way there is exactly one place to look if a
setting needs to change, and one place to check if something is missing.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load the .env file once, when this module is first imported.
load_dotenv()


def _get_tickers() -> list[str]:
    """Turn the comma-separated BANK_TICKERS env var into a clean list."""
    raw = os.getenv("BANK_TICKERS", "")
    tickers = [ticker.strip() for ticker in raw.split(",") if ticker.strip()]
    if not tickers:
        raise ValueError(
            "No tickers configured. Set BANK_TICKERS in your .env file, "
            "e.g. BANK_TICKERS=HDFCBANK.NS,ICICIBANK.NS"
        )
    return tickers


@dataclass(frozen=True)
class Settings:
    """All configuration the agent needs, loaded once at startup."""

    # --- Stock tracking ---
    tickers: list[str] = field(default_factory=_get_tickers)
    move_threshold_pct: float = float(os.getenv("MOVE_THRESHOLD_PCT", "3.0"))
    history_window_days: int = int(os.getenv("HISTORY_WINDOW_DAYS", "30"))
    moving_average_days: int = int(os.getenv("MOVING_AVERAGE_DAYS", "7"))

    # --- LLM (Ollama) ---
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # --- Email ---
    email_sender: str = os.getenv("EMAIL_SENDER", "")
    email_app_password: str = os.getenv("EMAIL_APP_PASSWORD", "")
    email_recipient: str = os.getenv("EMAIL_RECIPIENT", "")
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))

    # --- Storage ---
    db_path: str = os.getenv("DB_PATH", "data/agent_memory.db")

    # --- Scheduling defaults (only used the first time the cron job is set up) ---
    default_cron_hour: int = int(os.getenv("DEFAULT_CRON_HOUR", "8"))
    default_cron_minute: int = int(os.getenv("DEFAULT_CRON_MINUTE", "0"))


# A single shared instance other modules can import directly:
#   from src.config import settings
settings = Settings()
