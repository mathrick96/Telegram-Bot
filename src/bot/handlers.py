import os
import json
import zoneinfo
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from .paths import CONFIG_PATH
from .db import (
    log_all_users,
    get_user_data,
    create_new_user,
    save_new_user,
    update_user,
    delete_user,
)
from .scheduler import schedule_story_job


LANG, LEVEL, TIME, COMPLETE = range(4)

def chunk(lst, n):
    """Split a list into chunks of size ``n``."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


dummy_user = (000000000, "english", "A1", 0, "UTC", None)
ALL_TIMEZONES = sorted(zoneinfo.available_timezones())
ADMIN_ID = os.getenv("ADMIN_ID")

with open(CONFIG_PATH) as f:
    cfg = json.load(f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "👋 Hello and welcome to Daily Language Boost\\!\n"
            "I’ll send you one short, level\\-appropriate text **every day** in the language you choose, plus a few follow\\-up"
            "questions to keep you thinking\\.\n"
            "**How to get started**\n"
            "Start with the command /configure and tell me the following data\n"
            "1️⃣  Your target language\n"
            "2️⃣  Your CEFR level in that language \\(A1–C2\\)\n"
            "3️⃣  The local time you’d like to receive each text"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_user(user_id, configured=0)
    jobs = context.job_queue.get_jobs_by_name(str(user_id))
    for job in jobs:
        job.schedule_removal()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Daily delivery paused. Use /configure to resume.",
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "Available commands:\n"
            "/start - Introduction and setup instructions\n"
            "/configure - Configure language, level, timezone, and delivery time\n"
            "/stop - Pause daily delivery\n"
            "/cancel - Cancel the current setup\n"
            "/help - Show this help message"
        ),
    )



async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id = update.message.from_user.id
    text = update.message.text
    await update.message.reply_text(f"Your id: {id}, your message: {text}")


async def configure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the configuration and asks for the language"""
    user_id = update.message.from_user.id
    create_new_user(user_id)
    items = list(cfg["languages"].items())
    rows = chunk(items, 3)
    kb = [
        [InlineKeyboardButton(l[0], callback_data=f"{l[1]}") for l in row]
        for row in rows
    ]

    await update.message.reply_text(
        "Hey there!\nPlease selelct the name of the language that you want to study or select /cancel to abort.\n",
        reply_markup=InlineKeyboardMarkup(kb),
    )

    return LANG





async def lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    language = query.data
    if language not in cfg["languages"].values():
        await query.answer("Please use the buttons")
        return LANG
    await query.answer()
    context.user_data["language"] = language
    update_user(query.from_user.id, language=language)
    levels = cfg["cefr_levels"]
    rows = chunk(levels, 2)
    kb = [[InlineKeyboardButton(l, callback_data=f"{l}") for l in row] for row in rows]

    await query.edit_message_text(
        text=f"You chose {language}.\nNow select a level or type /cancel to abort",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return LEVEL


async def level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    level = query.data
    if level not in cfg["cefr_levels"]:
        await query.answer("Please use the buttons")
        return LEVEL
    await query.answer()
    context.user_data["level"] = level
    update_user(query.from_user.id, level=level)
    await query.edit_message_text(
        text=(
            f"You chose {level}.\n"
            "Send your timezone in 'Region/City' format (e.g., 'Europe/Berlin') or type /cancel to abort"
        )
    )
    return TIME


async def time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timezone first, then hour selection."""
    text = update.message.text.strip()
    kb = [[InlineKeyboardButton('OK', callback_data='ok'), InlineKeyboardButton('CANCEL', callback_data='/cancel')]]

    if "timezone" not in context.user_data:
        if text not in ALL_TIMEZONES:
            await update.message.reply_text(
                "Please send a valid timezone like 'Europe/Berlin' or type /cancel to abort",
            )
            return TIME
        context.user_data["timezone"] = text
        update_user(update.effective_user.id, timezone=text)
        await update.message.reply_text(
            "Timezone set. Now send the hour (0-23) for daily delivery or type /cancel to abort",
                            )
        return TIME

    if not text.isdigit() or not 0 <= int(text) <= 23:
        await update.message.reply_text(
            "Please send an hour as a number between 0 and 23.",
        )
        return TIME
    delivery_hour = int(text)
    context.user_data["delivery_hour"] = delivery_hour
    valid_time = f"{delivery_hour:02}:00"

    await update.message.reply_text(
        "Setup complete!\n"
        f"Language: {context.user_data['language']}\n"
        f"Level: {context.user_data['level']}\n"
        f"Timezone: {context.user_data['timezone']}\n"
        f"Delivery time: {valid_time}\n"
        "Press OK if you want to confirm the setup, CANCEL if you want to abort.",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return COMPLETE


async def complete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "ok":
        delivery_hour = context.user_data.get("delivery_hour")
        user_id = query.from_user.id
        update_user(user_id, delivery_hour=delivery_hour, configured=1)
        success, user = get_user_data(user_id)
        if success and user.get("delivery_hour") is not None and user.get("timezone"):
            run_time = schedule_story_job(context.job_queue, user)
            run_time_local = run_time.astimezone(ZoneInfo(user["timezone"]))
            next_time_str = run_time_local.strftime("%d-%m-%Y %H:%M %Z")
            await query.edit_message_text(
                f"Setup complete! Next story will be delivered at {next_time_str}. Use /help to see all commands."
            )
            return ConversationHandler.END
        await query.edit_message_text("Setup complete! Use /help to see all commands.")
    else:  # "cancel"
        await query.edit_message_text("Setup aborted. Run /configure to start over.")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Setup cancelled.")
    return ConversationHandler.END


async def insert_dummy_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    saved = save_new_user(dummy_user)
    if saved:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=("dummy user saved")
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=("error in saving dummy user")
        )


async def delete_dummy_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deleted = delete_user(dummy_user[0])
    if deleted:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=("dummy user deleted")
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=("error in deleting dummy user")
        )


async def log_db_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = log_all_users()
    if n is None:
        await update.message.reply_text("DB dump failed. Check server logs.")
    else:
        await update.message.reply_text(f"Logged {n} row(s) to server logs.")


async def delete_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID is None or str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return
    if not context.args:
        await update.message.reply_text("Usage: /deleteuser <user_id>")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user id")
        return
    deleted = delete_user(target_id)
    jobs = context.job_queue.get_jobs_by_name(str(target_id))
    for job in jobs:
        job.schedule_removal()
    if deleted:
        await update.message.reply_text(f"User {target_id} deleted")
    else:
        await update.message.reply_text(f"User {target_id} not found")