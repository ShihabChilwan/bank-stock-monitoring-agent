"""
Builds the email body and sends it through Gmail's SMTP server.
"""

import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import settings

DISCLAIMER = (
    "This is an automated summary for informational purposes only "
    "and does not constitute investment advice."
)


def compose_email_body(metrics: dict, insights: dict) -> str:
    """
    Build a plain-text email body: a summary table followed by one
    paragraph of commentary per ticker, followed by the disclaimer.

    `metrics` and `insights` are both dicts keyed by ticker symbol.
    """
    lines = [f"Bank Stock Summary - {date.today().isoformat()}", ""]

    # Summary table
    lines.append(f"{'Ticker':<15}{'Price':>10}{'% Change':>12}{'Flagged':>10}")
    lines.append("-" * 47)
    for ticker, ticker_metrics in metrics.items():
        flagged_label = "YES" if ticker_metrics["flagged"] else "no"
        lines.append(
            f"{ticker:<15}{ticker_metrics['price']:>10.2f}"
            f"{ticker_metrics['pct_change']:>11.2f}%{flagged_label:>10}"
        )
    lines.append("")

    # Per-ticker commentary
    for ticker, insight_text in insights.items():
        lines.append(f"{ticker}:")
        lines.append(insight_text)
        lines.append("")

    lines.append(DISCLAIMER)
    return "\n".join(lines)


def send_email(subject: str, body: str) -> None:
    """
    Send an email using the Gmail account configured in .env.
    Raises an exception on failure so the caller can log the failed attempt.
    """
    message = MIMEMultipart()
    message["From"] = settings.email_sender
    message["To"] = settings.email_recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.email_sender, settings.email_app_password)
        server.send_message(message)
