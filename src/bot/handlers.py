import os
import json
import zoneinfo
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler
from typing import List, TypeVar

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

T = TypeVar("T")

def chunk(lst: List[T], n: int) -> List[List[T]]:
    """Split ``lst`` into sublists of length ``n``."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


ALL_TIMEZONES = sorted(zoneinfo.available_timezones())
ADMIN_ID = os.getenv("ADMIN_ID")

with open(CONFIG_PATH) as f:
    cfg = json.load(f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message and setup instructions."""
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


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pause daily story delivery for the user."""
    user_id = update.effective_user.id
    update_user(user_id, paused=1)
    jobs = context.job_queue.get_jobs_by_name(str(user_id))
    for job in jobs:
        job.schedule_removal()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Daily delivery paused. Use /configure to resume.",
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display available bot commands."""
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



async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the sender's ID and message."""

    user_id = update.message.from_user.id

    text = update.message.text
    await update.message.reply_text(f"Your id: {user_id}, your message: {text}")

async def configure(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the configuration flow by asking for the target language."""
    user_id = update.message.from_user.id
    context.user_data.clear()
    create_new_user(user_id)
    success, user = get_user_data(user_id)
    context.user_data["timezone_changed"] = False
    context.user_data["delivery_hour_changed"] = False
    if success and user.get("configured"):
        tz = user.get("timezone")
        hour = user.get("delivery_hour")
        if tz:
            context.user_data["timezone"] = tz
        if hour is not None:
            context.user_data["delivery_hour"] = hour
    items = list(cfg["languages"].items())
    rows = chunk(items, 3)
    kb = [
        [InlineKeyboardButton(lang[0], callback_data=f"{lang[1]}") for lang in row]
        for row in rows
    ]

    await update.message.reply_text(
        "Hey there!\nPlease select the name of the language that you want to study or select /cancel to abort.\n",
        reply_markup=InlineKeyboardMarkup(kb),
    )

    return LANG





async def lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the chosen language and prompt for proficiency level."""
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
    kb = [[InlineKeyboardButton(level, callback_data=f"{level}") for level in row] for row in rows]
    await query.edit_message_text(
        text=f"You chose {language}.\nNow select a level or type /cancel to abort",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return LEVEL


async def level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Record the user's level and proceed to timezone configuration."""
    query = update.callback_query
    level = query.data
    if level not in cfg["cefr_levels"]:
        await query.answer("Please use the buttons")
        return LEVEL
    await query.answer()
    context.user_data["level"] = level
    update_user(query.from_user.id, level=level)
    if "timezone" in context.user_data and "delivery_hour" in context.user_data:
        delivery_hour = context.user_data["delivery_hour"]
        valid_time = f"{delivery_hour:02}:00"
        kb = [[InlineKeyboardButton('OK', callback_data='ok'), InlineKeyboardButton('CANCEL', callback_data='/cancel')]]
        await query.edit_message_text(
            "Setup complete!\n"
            f"Language: {context.user_data['language']}\n"
            f"Level: {context.user_data['level']}\n"
            f"Timezone: {context.user_data['timezone']}\n"
            f"Delivery time: {valid_time}\n"
            "Press OK if you want to confirm the setup, CANCEL if you want to abort.",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return COMPLETE
    await query.edit_message_text(
        text=(
            f"You chose {level}.\n"
            "Type part of your timezone (e.g., 'Europe' or 'Berlin').\n"
            "I'll show matching options, or type /cancel to abort"        )
    )
    return TIME


async def time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timezone selection and delivery hour input."""
    text = update.message.text.strip()

    if "timezone" not in context.user_data:
        matches = [tz for tz in ALL_TIMEZONES if text.lower() in tz.lower()]
        if not matches:
            await update.message.reply_text(
                "No matching timezones found. Try again or type /cancel to abort",
            )
            return TIME
        kb = [
            [InlineKeyboardButton(tz, callback_data=tz) for tz in row]
            for row in chunk(matches[:9], 3)
        ]

        await update.message.reply_text(
            "Select your timezone from the options below or type again to narrow your search",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return TIME
    
    
    if "delivery_hour" not in context.user_data:
        if not text.isdigit() or not 0 <= int(text) <= 23:
            await update.message.reply_text(
                "Please send an hour as a number between 0 and 23.",
            )
            return TIME
        delivery_hour = int(text)
        context.user_data["delivery_hour"] = delivery_hour
        context.user_data["delivery_hour_changed"] = True
        valid_time = f"{delivery_hour:02}:00"


        kb = [[InlineKeyboardButton('OK', callback_data='ok'), InlineKeyboardButton('CANCEL', callback_data='/cancel')]]
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

    # Should not reach here if both timezone and delivery hour are present
    return COMPLETE

async def timezone_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store selected timezone and ask for delivery hour."""
    query = update.callback_query
    tz = query.data
    if tz not in ALL_TIMEZONES:
        await query.answer("Invalid selection")
        return TIME
    await query.answer()
    context.user_data["timezone"] = tz
    context.user_data["timezone_changed"] = True
    update_user(query.from_user.id, timezone=tz)
    await query.edit_message_text(
        f"Timezone set to {tz}. Now send the hour (0-23) for daily delivery or type /cancel to abort"
    )
    return TIME



async def complete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finalize configuration or cancel based on user choice."""
    query = update.callback_query
    await query.answer()

    if query.data == "ok":
        user_id = query.from_user.id
        update_kwargs = {
            "configured": 1,
            "language": context.user_data.get("language"),
            "level": context.user_data.get("level"),
            "paused": 0,
        }
        if context.user_data.get("timezone_changed"):
            update_kwargs["timezone"] = context.user_data.get("timezone")
        if context.user_data.get("delivery_hour_changed"):
            update_kwargs["delivery_hour"] = context.user_data.get("delivery_hour")
        update_user(user_id, **update_kwargs)
        success, user = get_user_data(user_id)
        if success and user.get("delivery_hour") is not None and user.get("timezone"):
            run_time = schedule_story_job(context.job_queue, user)
            if run_time is not None:
                if run_time.tzinfo is None:
                    run_time = run_time.replace(tzinfo=ZoneInfo("UTC"))
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
    """Abort the current configuration conversation."""
    await update.message.reply_text("Setup cancelled.")
    return ConversationHandler.END




async def log_db_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log all users to the server logs."""
    n = log_all_users()
    if n is None:
        await update.message.reply_text("DB dump failed. Check server logs.")
    else:
        await update.message.reply_text(f"Logged {n} row(s) to server logs.")


async def delete_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a user by ID. Only available to the admin."""
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
