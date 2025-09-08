import logging
import sqlite3
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes, JobQueue
from typing import Any, Dict, List, cast

from .paths import DB_PATH
from .story import generate_text
from .db import get_user_data, update_user


def load_all_users() -> List[Dict[str, Any]]:
    """Fetch all configured, unpaused users from the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE configured = 1 AND paused = 0")
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logging.error(f"Error loading users: {e}")
        return []


def schedule_story_job(job_queue: JobQueue, user: Dict[str, Any]) -> datetime:
    """Schedule a daily story job for ``user`` and return its next run time."""
    delivery_hour = user["delivery_hour"]
    tz = ZoneInfo(user["timezone"])
    daily_time = time(hour=delivery_hour, minute=0, tzinfo=tz)
    # Remove any existing scheduled jobs for this user before scheduling a new one
    for job in job_queue.get_jobs_by_name(str(user["user_id"])):
        job.schedule_removal()

    job = job_queue.run_daily(
        send_story,
        time=daily_time,
        chat_id=user["user_id"],
        name=str(user["user_id"]),
        data={"user_id": user["user_id"]},
    )
    next_run_time = getattr(job, "next_run_time", None)
    if next_run_time is None:
        now = datetime.now(tz)
        next_run_time = datetime.combine(now.date(), daily_time)
        if next_run_time <= now:
            next_run_time += timedelta(days=1)
    return next_run_time

async def send_story(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a story to the user associated with the job."""

    job = context.job
    if job is None or job.data is None:
        return
    job_data = cast(Dict[str, Any], job.data)
    user_id = job_data["user_id"]
    _, user = get_user_data(user_id)
    if not user:
        return

    story_text = await generate_text(user["language"], user["level"])
    await context.bot.send_message(chat_id=user_id, text=story_text)
    timestamp = datetime.utcnow().isoformat()
    update_user(user_id, last_sent=timestamp)


def restart_jobs(job_queue: JobQueue) -> None:
    """Reschedule story jobs for all active users."""
    for user in load_all_users():
        if user.get("delivery_hour") is not None and user.get("timezone"):
            schedule_story_job(job_queue, user)