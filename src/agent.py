"""
The bank stock monitoring agent.

Built the way agents are usually taught: a handful of plain Python
functions marked with @tool, a system prompt describing the job, and
langchain's create_agent() tying them together. The agent decides which
tool to call and in what order - we don't hard-code the sequence with a
custom graph.
"""

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_ollama import ChatOllama

from src.config import settings
from src.tools import email_sender, memory, stock_data
from src.tools.metrics import calculate_metrics

ADVISORY_KEYWORDS = [
    "buy",
    "sell",
    "invest now",
    "should purchase",
    "strong buy",
    "recommend buying",
    "recommend selling",
]


def contains_advisory_language(text: str) -> bool:
    """
    A simple keyword check that catches obvious buy/sell/invest language.
    This is the output-side guardrail: even though the system prompt
    already tells the model not to give advice, small local models don't
    always follow instructions perfectly, so the output gets checked too.
    """
    lowered = text.lower()
    return any(keyword in lowered for keyword in ADVISORY_KEYWORDS)


model = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url)


@tool
def get_ticker_metrics(ticker: str) -> dict:
    """
    Fetch the current price and recent price history for a bank stock
    ticker, and return its day-over-day % change, moving average,
    volatility, and whether the move is large enough to be flagged.
    """
    current_price = stock_data.fetch_current_price(ticker)
    price_history = stock_data.fetch_historical_prices(ticker, settings.history_window_days)
    return calculate_metrics(current_price, price_history)


@tool
def get_previous_insight(ticker: str) -> str:
    """
    Return the insight that was written about this ticker last time it
    was checked, so today's summary can reference how things have
    changed. If there's no previous note, says so.
    """
    previous = memory.get_last_insight(ticker)
    return previous if previous else "No previous note - this is the first check for this ticker."


@tool
def record_insight(
    ticker: str,
    price: float,
    pct_change: float,
    moving_avg: float,
    volatility: float,
    flagged: bool,
    insight_text: str,
) -> str:
    """
    Save today's metrics and insight for a ticker to persistent storage,
    so future runs can look back at what was said today. If the insight
    text contains buy/sell/investment language, it is replaced with a
    safe, purely descriptive line before being saved.
    """
    if contains_advisory_language(insight_text):
        print(f"[guardrail] Advisory language detected for {ticker}, using a safe fallback line.")
        insight_text = (
            f"{ticker} moved {pct_change}% today, with volatility of {volatility}%. "
            "No further commentary is available for this update."
        )

    memory.save_daily_metrics(
        ticker,
        {
            "price": price,
            "pct_change": pct_change,
            "moving_avg": moving_avg,
            "volatility": volatility,
            "flagged": flagged,
        },
    )
    memory.save_insight(ticker, insight_text)
    return f"Saved today's metrics and insight for {ticker}."


@tool
def send_summary_email(email_body: str, trigger_type: str) -> str:
    """
    Send the final summary email. `trigger_type` must be either
    "scheduled" or "manual". If trigger_type is "scheduled" and an
    automatic email has already gone out today, nothing is sent and a
    message says so instead - this avoids duplicate automatic emails.
    Manual runs always send.
    """
    if trigger_type == "scheduled" and memory.was_scheduled_email_sent_today():
        return "An automatic email was already sent today - skipping to avoid a duplicate."

    try:
        email_sender.send_email("Bank Stock Summary", email_body)
        memory.log_email_sent(trigger_type=trigger_type, status="sent")
        return "Email sent successfully."
    except Exception as error:  # noqa: BLE001 - we want to log and report the failure either way
        memory.log_email_sent(trigger_type=trigger_type, status="failed")
        return f"Failed to send email: {error}"


TOOLS = [get_ticker_metrics, get_previous_insight, record_insight, send_summary_email]

SYSTEM_PROMPT = f"""You are a bank stock monitoring assistant. Each time you are asked to
run, you must do the following for every one of these tickers, in order:
{", ".join(settings.tickers)}

For EACH ticker:
1. Call get_ticker_metrics to fetch today's numbers.
2. Call get_previous_insight to see what you said about it last time.
3. Write a short (2-3 sentence) plain-English performance summary using
   the metrics and the previous note for context.
4. IMPORTANT: give descriptive commentary only. Never give investment
   advice, price predictions, or buy/sell/hold recommendations.
5. Call record_insight to save the metrics and the summary you wrote.

After every ticker has been processed:
6. Combine everything into a single email body: a short table listing each
   ticker's price, % change, and flagged status, followed by each ticker's
   summary, followed by exactly this disclaimer line: "This is an
   automated summary for informational purposes only and does not
   constitute investment advice."
7. Call send_summary_email exactly once with the full email body. The
   user's message will tell you whether this is a "scheduled" or "manual"
   run - pass that as the trigger_type argument.

Do not skip any ticker, and do not skip sending the email.
"""

agent = create_agent(model=model, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
