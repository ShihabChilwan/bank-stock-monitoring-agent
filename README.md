# Bank Stock Monitoring Agent

An AI agent that tracks bank stock performance daily, writes plain-English insights with a local LLM, and emails a summary. Built with LangChain's `create_agent`, SQLite-backed memory, and cron scheduling, and controllable from a small Streamlit dashboard.

> This agent gives descriptive commentary only. It does not provide investment advice, predictions, or buy/sell/hold recommendations.

## Features

- Tracks any list of tickers (default setup uses NSE bank stocks)
- Computes day-over-day % change, moving average, and volatility with plain pandas
- Flags large moves based on a configurable threshold
- Writes a short summary per ticker using a local Ollama model
- Remembers past insights, so today's summary can reference the previous one
- Sends one summary email per run through Gmail SMTP
- Skips duplicate scheduled emails on the same day
- Streamlit dashboard with a manual run button, email history, and a cron time picker

## Tech Stack

- **Agent:** LangChain `create_agent` (runs on LangGraph underneath)
- **LLM:** Ollama, default model `qwen2.5:7b-instruct`
- **Data:** yfinance, pandas
- **Storage:** SQLite
- **Scheduling:** cron, via `python-crontab`
- **UI:** Streamlit
- **Tests:** pytest

## Project Structure

```
bank-stock-monitoring-agent/
├── src/
│   ├── agent.py            # Agent, tools, system prompt, guardrail
│   ├── config.py           # Settings loaded from .env
│   └── tools/
│       ├── email_sender.py # Gmail SMTP sender
│       ├── memory.py       # SQLite memory (metrics, insights, email log)
│       ├── metrics.py      # Deterministic metric calculations
│       ├── scheduler.py    # Reads and writes the cron job
│       └── stock_data.py   # yfinance fetching with retry
├── tests/
│   └── test_metrics.py
├── app.py                  # Streamlit dashboard
├── main.py                 # Entry point for scheduled runs
├── requirements.txt
└── .env.example
```

## Setup

1. Clone the repo and create a virtual environment.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your values (see Configuration).
4. Install Ollama and pull the model:
   ```
   ollama pull qwen2.5:7b-instruct
   ```
5. Run once manually to check everything works:
   ```
   python main.py
   ```
6. Launch the dashboard:
   ```
   streamlit run app.py
   ```

## Configuration

All settings are read from `.env`.

- `BANK_TICKERS`: comma-separated tickers, e.g. `HDFCBANK.NS,ICICIBANK.NS` (required)
- `MOVE_THRESHOLD_PCT`: % move that gets flagged (default `3.0`)
- `HISTORY_WINDOW_DAYS`: days of history to fetch (default `30`)
- `MOVING_AVERAGE_DAYS`: moving average window (default `7`)
- `OLLAMA_MODEL`: model name (default `qwen2.5:7b-instruct`)
- `OLLAMA_BASE_URL`: Ollama server URL (default `http://localhost:11434`)
- `EMAIL_SENDER`: Gmail address used to send
- `EMAIL_APP_PASSWORD`: Gmail app password (not your normal password)
- `EMAIL_RECIPIENT`: where the summary is sent
- `SMTP_SERVER` / `SMTP_PORT`: default `smtp.gmail.com` / `587`
- `DB_PATH`: SQLite file location (default `data/agent_memory.db`)
- `DEFAULT_CRON_HOUR` / `DEFAULT_CRON_MINUTE`: initial schedule (default 08:00)

## How It Works

```
User message: "Run today's check. trigger_type = scheduled / manual"
   -> get_ticker_metrics for each ticker
   -> get_previous_insight for each ticker
   -> agent writes a short summary per ticker
   -> record_insight saves each one (guardrail applied here)
   -> agent composes the full email body
   -> send_summary_email called once
      (scheduled runs skip if an automatic email already went out today)
```

- The agent decides the order of tool calls itself. There is no hand-built graph.
- The LLM writes the summaries. All numbers come from deterministic Python, not the LLM, so they stay trustworthy and easy to verify.

## Guardrails

- **Prompt-level:** the system prompt tells the model to give descriptive commentary only.
- **Output-level:** `record_insight` scans the text for advisory keywords (buy, sell, etc.) before saving. If any are found, it is replaced with a safe, purely numeric fallback line.
- **Limitation:** this is a simple keyword check, so it catches obvious cases but not every phrasing.

## Running Tests

The tests use synthetic data, so no network is needed. `BANK_TICKERS` must be set because the config requires it.

```
BANK_TICKERS=TEST.NS pytest
```

## Known Limitations

- Cron runs on the machine where it is set up, so scheduled runs pause when that machine or container is off. A real deployment would use an always-on host or a cloud scheduler.
- Cron precision is one minute.
- `scheduler.py` hard-codes `/usr/bin/python3` as the interpreter, so it may need changing if you use a virtual environment.
- Small local models do not always follow instructions perfectly, which is why the output guardrail exists.
- If you run Ollama on a GPU, check with `ollama ps` that the model is loaded on the GPU and not silently on CPU.

## Out of Scope

- RAG or document grounding
- Multi-user support
- Real-time or intraday tracking (daily granularity only)

## Disclaimer

This is a hobby project. Output is for informational purposes only and is not investment advice.