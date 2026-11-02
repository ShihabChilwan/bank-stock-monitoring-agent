"""
Entry point for the scheduled (cron) run.

This just sets up the database, sends one message to the agent telling it
this is a scheduled run, and prints what the agent did. All the real work
happens inside the agent's tool calls (see src/agent.py).
"""

from langchain.messages import HumanMessage

from src.agent import agent
from src.tools import memory


def run_scheduled():
    """Ask the agent to do today's check, as an automatic (cron-triggered) run."""
    memory.init_db()

    message = HumanMessage(
        content="Run today's check now. This is a SCHEDULED run - use trigger_type='scheduled'."
    )

    # A plain invoke() is used here (not stream()) because this runs
    # headless via cron - there's no one watching live output.
    result = agent.invoke({"messages": [message]})

    final_reply = result["messages"][-1].content
    print("[main] Scheduled run complete. Agent's final message:")
    print(final_reply)


if __name__ == "__main__":
    run_scheduled()
