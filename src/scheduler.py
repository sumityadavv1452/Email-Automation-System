"""
APScheduler daily cron job scheduler module.
"""

import sys
from typing import Callable
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from src.logger import app_logger

def schedule_daily_job(job_func: Callable[[], None], time_str: str) -> None:
    """
    Schedules a recurring daily job using APScheduler at the specified HH:MM time.

    Args:
        job_func: Function to execute on schedule.
        time_str: Time string in format "HH:MM" (e.g. "09:00").
    """
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format (e.g., '09:00')")

        hour = int(parts[0])
        minute = int(parts[1])

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Hour must be 00-23 and Minute must be 00-59")
    except Exception as e:
        app_logger.error(f"Invalid schedule time argument '{time_str}': {str(e)}")
        sys.exit(1)

    scheduler = BlockingScheduler()
    trigger = CronTrigger(hour=hour, minute=minute)

    scheduler.add_job(
        job_func,
        trigger=trigger,
        id="email_bulk_dispatch_job",
        name=f"Daily Bulk Email Dispatch at {time_str}",
        replace_existing=True,
    )

    app_logger.info(f"Scheduler active. Job scheduled daily at {time_str} (HH:MM). Press Ctrl+C to exit.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        app_logger.info("Scheduler stopped by user.")
