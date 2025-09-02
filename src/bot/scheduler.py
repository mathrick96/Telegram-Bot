import logging
import sqlite3
from datetime import datetime, timedelta, timezone
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


def compute_next_run(delivery_time, user_timezone):
    now = datetime.now(ZoneInfo(user_timezone))
    hour, minute = map(int, delivery_time.split(":")[:2])
    run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_time <= now:
        run_time += timedelta(days=1)
    return run_time


def schedule_story_job(job_queue, user):
    delivery_time = user.get("pending_delivery_time") or user["delivery_time"]
    run_time = compute_next_run(delivery_time, user["timezone"])
    if user.get("last_sent"):
        try:
            last_sent_utc = datetime.fromisoformat(user["last_sent"]).replace(
                tzinfo=timezone.utc
            )
            last_sent_local = last_sent_utc.astimezone(ZoneInfo(user["timezone"]))
            min_run_time = last_sent_local + timedelta(hours=24)
            while run_time < min_run_time:
                run_time += timedelta(days=1)
        except ValueError:
            pass

    # Remove any existing scheduled jobs for this user before scheduling a new one
    for job in job_queue.get_jobs_by_name(str(user["user_id"])):
        job.schedule_removal()


    job_queue.run_once(
        send_story,
        when=run_time,
        chat_id=user["user_id"],
        name=str(user["user_id"]),
        data={
            "user_id": user["user_id"],
            "timezone": user["timezone"],
            "delivery_time": delivery_time,
        },
    )
    return run_time


async def send_story(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]
    _, user = get_user_data(user_id)
    if not user:
        return
    tz = ZoneInfo(user["timezone"])
    now_local = datetime.now(tz)
    if user.get("last_sent"):
        try:
            last_sent_utc = datetime.fromisoformat(user["last_sent"]).replace(
                tzinfo=timezone.utc
            )
            last_sent_local = last_sent_utc.astimezone(tz)
            if now_local - last_sent_local < timedelta(hours=24):
                return
        except ValueError:
            return
    
    story_text = await generate_text(user["language"], user["level"])
    await context.bot.send_message(chat_id=user_id, text=story_text)
    timestamp = datetime.utcnow().isoformat()
    if user.get("pending_delivery_time"):
        delivery_time = user["pending_delivery_time"]
        update_user(
            user_id,
            delivery_time=delivery_time,
            pending_delivery_time=None,
            last_sent=timestamp,
        )
        user["delivery_time"] = delivery_time
        user["pending_delivery_time"] = None
    else:
        update_user(user_id, last_sent=timestamp)
    user["last_sent"] = timestamp
    schedule_story_job(context.job_queue, user)


def restart_jobs(job_queue):
    for user in load_all_users():
        if user.get("delivery_time") and user.get("timezone"):
            schedule_story_job(job_queue, user)