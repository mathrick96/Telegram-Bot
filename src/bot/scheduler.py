import logging
import sqlite3
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes

from .paths import DB_PATH
from .story import generate_text
from .db import get_user_data, update_user


def load_all_users():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE configured = 1")
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logging.error(f"Error loading users: {e}")
        return []


def schedule_story_job(job_queue, user):
    daily_time = time(
        hour=user["delivery_hour"], minute=0, tzinfo=ZoneInfo(user["timezone"])
    )
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
    return job.next_t

async def send_story(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]
    _, user = get_user_data(user_id)
    if not user:
        return

    story_text = await generate_text(user["language"], user["level"])
    await context.bot.send_message(chat_id=user_id, text=story_text)
    timestamp = datetime.utcnow().isoformat()
    update_user(user_id, last_sent=timestamp)


def restart_jobs(job_queue):
    for user in load_all_users():
        if user.get("delivery_hour") is not None and user.get("timezone"):
            schedule_story_job(job_queue, user)