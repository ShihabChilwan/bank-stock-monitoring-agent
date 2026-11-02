"""
Manages the cron schedule for the daily agent run.

This edits the *real* user crontab (not a simulated timer), so changing
the time from the Streamlit app genuinely reschedules the actual job.
A single comment tag is used to find and replace our one job without
disturbing any other cron entries the user might have.
"""

from pathlib import Path

from crontab import CronTab

JOB_COMMENT = "bank_stock_agent"


def _project_root() -> Path:
    """The folder this project lives in, so the cron command uses an absolute path."""
    return Path(__file__).resolve().parent.parent.parent


def get_current_schedule() -> tuple[int, int] | None:
    """
    Return (hour, minute) for the currently scheduled job, or None if no
    job has been set up yet.
    """
    cron = CronTab(user=True)
    for job in cron.find_comment(JOB_COMMENT):
        return job.hour, job.minute
    return None


def set_schedule(hour: int, minute: int) -> None:
    """
    Create or update the cron job so it runs main.py at the given time,
    every day. Removes any previous version of this job first so we never
    end up with duplicates.
    """
    cron = CronTab(user=True)
    cron.remove_all(comment=JOB_COMMENT)

    main_script = _project_root() / "main.py"
    log_file = _project_root() / "logs" / "cron.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    command = f"/usr/bin/python3 {main_script} >> {log_file} 2>&1"
    job = cron.new(command=command, comment=JOB_COMMENT)
    job.hour.on(hour)
    job.minute.on(minute)
    cron.write()
