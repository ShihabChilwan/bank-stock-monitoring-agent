"""
Streamlit dashboard for the Bank Stock Monitoring Agent.

Three things live here:
  1. A "Send Updated Email Now" button - a manual run, useful for demos.
     While it runs, we stream the agent's output and show which tool it
     is calling, the same way the mentor's example does.
  2. A history of past emails (scheduled vs. manual).
  3. A time picker that rewrites the actual cron schedule.
"""

import datetime as dt

import streamlit as st
from langchain.messages import AIMessageChunk, HumanMessage

from src.agent import agent
from src.config import settings
from src.tools import memory, scheduler

st.set_page_config(page_title="Bank Stock Monitoring Agent", layout="centered")
st.title("Bank Stock Monitoring Agent")

memory.init_db()

# --- Section 1: run the agent and watch it work ---

st.subheader("Latest Run")

if st.button("Send Updated Email Now", type="primary"):
    message = HumanMessage(
        content="Run today's check now. This is a MANUAL run - use trigger_type='manual'."
    )

    status_line = st.empty()
    reply_box = st.empty()
    full_reply = ""

    # stream_mode="messages" gives us each small piece of the agent's
    # reply as it's generated, plus tool_call_chunks whenever the agent
    # decides to call one of its tools - this is what lets us show
    # "Calling get_ticker_metrics..." live instead of one long wait.
    for chunk, _metadata in agent.stream({"messages": [message]}, stream_mode="messages"):
        if isinstance(chunk, AIMessageChunk):
            full_reply += chunk.content
            reply_box.markdown(full_reply)

        for tool_call in getattr(chunk, "tool_call_chunks", []):
            tool_name = tool_call.get("name")
            if tool_name:
                status_line.info(f"Calling tool: **{tool_name}**")

    status_line.empty()
    st.success("Run complete - check your inbox for the email.")

    st.markdown("### Today's Metrics & Insights")
    snapshot = memory.get_latest_snapshot()
    if snapshot:
        st.table([{"Ticker": ticker, **values} for ticker, values in snapshot.items()])
    else:
        st.write("No data recorded for today yet.")

# --- Section 2: email history ---

st.subheader("Email History")
history = memory.get_email_history(limit=10)
if history:
    st.table(
        [
            {"Date": row[0], "Sent At": row[1], "Status": row[2], "Trigger": row[3]}
            for row in history
        ]
    )
else:
    st.write("No emails sent yet.")

# --- Section 3: schedule picker ---

st.subheader("Daily Schedule")

current_schedule = scheduler.get_current_schedule()
if current_schedule:
    default_hour, default_minute = current_schedule
else:
    default_hour, default_minute = settings.default_cron_hour, settings.default_cron_minute

chosen_time = st.time_input(
    "Run the agent automatically every day at:",
    value=dt.time(hour=default_hour, minute=default_minute),
)

if st.button("Update Schedule"):
    scheduler.set_schedule(chosen_time.hour, chosen_time.minute)
    st.success(
        f"Cron job updated to run daily at {chosen_time.strftime('%H:%M')}. "
        "Note: cron re-checks its schedule roughly once a minute, so the "
        "change may take a moment to take effect."
    )
