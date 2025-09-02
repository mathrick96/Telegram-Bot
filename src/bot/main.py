import logging, os
import sqlite3
import json
import zoneinfo
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode
from .paths import CONFIG_PATH, DATA_DIR, DB_PATH
from .story import generate_text

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
def chunk(lst, n):
    """Split a list into chunks of size ``n``."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


dummy_user = (000000000, "english", "A1", "00:00:00", "UTC", None, None)

ALL_TIMEZONES = sorted(zoneinfo.available_timezones())
load_dotenv()
bot_key = os.getenv("TELEGRAM_BOT_KEY")
if not bot_key:
    logging.critical("TELEGRAM_BOT_KEY is not set in environment variables")
    raise RuntimeError("Missing TELEGRAM_BOT_KEY environment variable")

ADMIN_ID = os.getenv("ADMIN_ID")


if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

with open(CONFIG_PATH) as f:
    cfg = json.load(f)

# database connection and table creation
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        language TEXT,
        level TEXT,
        delivery_time TEXT,
        timezone TEXT,
        last_sent TEXT,
        pending_delivery_time TEXT,
        configured INTEGER 
    )
"""
)

conn.close()

######################################################################################
############################   HELPER FUNCTIONS   ####################################
######################################################################################


def log_all_users():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT user_id, language, level, delivery_time, timezone, last_sent, pending_delivery_time, configured                
                FROM users
                ORDER BY user_id
            """
            )
            rows = cur.fetchall()
            logging.info("DB dump: %d row(s) in users.", len(rows))
            for r in rows:
                logging.info(
                    "user_id=%s | language=%s | level=%s | delivery_time=%s | timezone=%s | last_sent=%s | pending_delivery_time=%s | configured=%s",
                    r["user_id"],
                    r["language"],
                    r["level"],
                    r["delivery_time"],
                    r["timezone"],
                    r["last_sent"],
                    r["pending_delivery_time"],
                    r["configured"],
                )
            return len(rows)
    except Exception as e:
        logging.exception("DB dump failed: %s", e)
        return None


def get_user_data(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                logging.info(f"Retrieved user_id {user_id} successfully.")
                return True, dict(row)
            else:
                logging.warning(f"No user found with user_id {user_id}.")
                return False, None
    except Exception as e:
        logging.error(f"Error retrieving user_id {user_id}: {e}")
        return False, None


def create_new_user(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO users
                (user_id, configured)
                VALUES (?, 0)
            """,
                (user_id,),
            )
            conn.commit()
            if cur.rowcount > 0:
                logging.info(f"Inserted new user_id {user_id} successfully.")
                return True
            else:
                logging.warning(f"User_id {user_id} already exists. No insertion.")
                return False
    except Exception as e:
        logging.error(f"Error inserting user_id {user_id}: {e}")
        return False


def save_new_user(user_data):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO users
                (user_id, language, level, delivery_time, timezone, last_sent, pending_delivery_time, configured)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, 
                user_data
            )
            conn.commit()
            if cur.rowcount > 0:
                logging.info(f"Inserted new user_id {user_data[0]} successfully.")
                return True
            else:
                logging.warning(f"User_id {user_data[0]} already exists. No insertion.")
                return False
    except Exception as e:
        logging.error(f"Error inserting user_id {user_data[0]}: {e}")
        return False


def update_user(
    user_id,
    language=None,
    level=None,
    delivery_time=None,
    timezone=None,
    configured=None,
    last_sent=None,
    pending_delivery_time=None,
):
    fields, values = [], []
    if language is not None:
        fields.append("language = ?")
        values.append(language)
    if level is not None:
        fields.append("level = ?")
        values.append(level)
    if delivery_time is not None:
        fields.append("delivery_time = ?")
        values.append(delivery_time)
    if timezone is not None:
        fields.append("timezone = ?")
        values.append(timezone)
    if configured is not None:
        fields.append("configured = ?")
        values.append(configured)
    if last_sent is not None:
        fields.append("last_sent = ?")
        values.append(last_sent)
    if pending_delivery_time is not None:
        fields.append("pending_delivery_time = ?")
        values.append(pending_delivery_time)
    if not fields:
        return False  # nothing to update
    values.append(user_id)
    db_query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(db_query, values)
            conn.commit()
            if cur.rowcount > 0:
                logging.info(f"Updated user_id {user_id} successfully.")
                return True
            else:
                logging.warning(
                    f"No user found with user_id {user_id}. Update skipped."
                )
                return False
    except Exception as e:
        logging.error(f"Error updating user_id {user_id}: {e}")
        return False
    

def delete_user(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            if cur.rowcount > 0:
                logging.info(f"Deleted user_id {user_id} successfully.")
                return True
            else:
                logging.warning(
                    f"No user found with user_id {user_id}. Deletion skipped."
                )
                return False
    except Exception as e:
        logging.error(f"Error deleting user_id {user_id}: {e}")
        return False


######################################################################################
##############################   SCHEDULING   #######################################
######################################################################################


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
    tz = ZoneInfo(user["timezone"])
    today = datetime.now(tz).date()
    if user.get("last_sent") == today.isoformat() and run_time.date() == today:
        run_time += timedelta(days=1)
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
    tz = user["timezone"]
    today = datetime.now(ZoneInfo(tz)).date().isoformat()
    if user.get("last_sent") == today:
        return
    story_text = generate_text(user["language"], user["level"])
    await context.bot.send_message(chat_id=user_id, text=story_text)
    if user.get("pending_delivery_time"):
        delivery_time = user["pending_delivery_time"]
        update_user(
            user_id,
            delivery_time=delivery_time,
            pending_delivery_time=None,
            last_sent=today,
        )
        user["delivery_time"] = delivery_time
        user["pending_delivery_time"] = None
    else:
        update_user(user_id, last_sent=today)
    user["last_sent"] = today
    schedule_story_job(context.job_queue, user)


def restart_jobs(job_queue):
    for user in load_all_users():
        if user.get("delivery_time") and user.get("timezone"):
            schedule_story_job(job_queue, user)


######################################################################################
############################   MESSAGES & COMMANDS   #################################
######################################################################################


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "👋 Hello and welcome to Daily Language Boost\\!\n"
            "I’ll send you one short, level\\-appropriate text **every day** in the language you choose, plus a few follow\\-up questions to keep you thinking\\.\n"
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

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id = update.message.from_user.id
    text = update.message.text
    await update.message.reply_text(f"Your id: {id}, your message: {text}")


LANG, LEVEL, TIMEZONE, TIME, COMPLETE, RECONFIRM = range(6)


async def configure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    "Starts the configuration and asks for the language"
    user_id = update.message.from_user.id
    context.user_data["skip_timezone"] = False
    _, user = get_user_data(user_id)
    if user and user.get("configured") == 1:
        kb = [
            [
                InlineKeyboardButton("Yes", callback_data="yes"),
                InlineKeyboardButton("No", callback_data="no"),
            ]
        ]
        await update.message.reply_text(
            "You are already configured. Do you want to reconfigure?",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return RECONFIRM
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


async def reconfirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "yes":
        context.user_data["skip_timezone"] = True
        update_user(query.from_user.id, configured=0)
        items = list(cfg["languages"].items())
        rows = chunk(items, 3)
        kb = [
            [InlineKeyboardButton(l[0], callback_data=f"{l[1]}") for l in row]
            for row in rows
        ]
        await query.edit_message_text(
            "Hey there!\nPlease selelct the name of the language that you want to study or select /cancel to abort.\n",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return LANG
    await query.edit_message_text("Okay, configuration unchanged.")
    return ConversationHandler.END


async def lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = query.data
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
    await query.answer()
    level = query.data
    context.user_data["level"] = level
    update_user(query.from_user.id, level=level)
    if context.user_data.get("skip_timezone"):
        await query.edit_message_text(
            text=f"You chose {level}.\nNow select a delivery time in the form HH:MM or type /cancel to abort"
        )
        return TIME
    await query.edit_message_text(
        text=(
            f"You chose {level}.\n"
            "Send part of your timezone name (e.g., 'Berlin' or 'UTC') to search, or type /cancel to abort"
        )
    )
    return TIMEZONE


async def timezone_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    exact = next((tz for tz in ALL_TIMEZONES if tz.lower() == query_text.lower()), None)
    if exact:
        context.user_data["timezone"] = exact
        update_user(update.effective_user.id, timezone=exact)
        await update.message.reply_text(
            "Timezone set to {}. Now select a delivery time in the form HH:MM or type /cancel to abort".format(
                exact
            )
        )
        return TIME
    matches = [tz for tz in ALL_TIMEZONES if query_text.lower() in tz.lower()]
    if not matches:
        await update.message.reply_text(
            "No matches found. Please try again or type /cancel to abort"
        )
        return TIMEZONE
    matches = matches[:10]
    rows = chunk(matches, 2)
    kb = [
        [
            InlineKeyboardButton("OK", callback_data="ok"),
            InlineKeyboardButton("CANCEL", callback_data="/cancel"),
        ]
    ]
    await update.message.reply_text(
        "Select your timezone:", reply_markup=InlineKeyboardMarkup(kb)
    )
    return TIMEZONE


async def timezone_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tz = query.data
    context.user_data["timezone"] = tz
    update_user(query.from_user.id, timezone=tz)
    await query.edit_message_text(
        text=f"You chose {tz}.\nNow select a delivery time in the form HH:MM or type /cancel to abort"
    )
    return TIME

async def time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive a HH:MM string and finalize configuration."""
    time_text = update.message.text.strip()
    kb = [[InlineKeyboardButton('OK', callback_data='ok'), InlineKeyboardButton('CANCEL', callback_data='/cancel')]]
    # Validate time format
    try:
        valid_time = datetime.strptime(time_text, "%H:%M").strftime("%H:%M")
    except ValueError:
        await update.message.reply_text(
            "Please send the time in 24‑hour HH:MM format (e.g., 18:30)."
        )
        return TIME

    context.user_data["time"] = valid_time

    await update.message.reply_text(
        "Setup complete!\n"
        f"Language: {context.user_data['language']}\n"
        f"Level: {context.user_data['level']}\n"
        f"Delivery time: {valid_time}\n"
        "Press OK if you want to confirm the setup, CANCEL if you want to abort.",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return COMPLETE


async def complete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "ok":
        chosen_time = context.user_data.get("time")
        user_id = query.from_user.id
        success, user = get_user_data(user_id)
        if success and user.get("timezone"):
            tz = user["timezone"]
            today = datetime.now(ZoneInfo(tz)).date().isoformat()
            if user.get("last_sent") == today:
                update_user(user_id, pending_delivery_time=chosen_time, configured=1)
            else:
                update_user(user_id, delivery_time=chosen_time, configured=1)
                user["delivery_time"] = chosen_time
            success, user = get_user_data(user_id)
            if success and user.get("delivery_time") and user.get("timezone"):
                run_time = schedule_story_job(context.job_queue, user)
                next_time_str = run_time.strftime("%d-%m-%Y %H:%M %Z")
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



######################################################################################
###############################   DIAGNOSTICS   ######################################
######################################################################################


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


######################################################################################
##################################   MAIN    #########################################
######################################################################################


if __name__ == "__main__":
    application = ApplicationBuilder().token(bot_key).build()

    # message handler
    #application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    # diagnostics
    application.add_handler(CommandHandler("dummy", insert_dummy_user))
    application.add_handler(CommandHandler("deldummy", delete_dummy_user))
    application.add_handler(CommandHandler("logdb", log_db_cmd))

    # command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("deleteuser", delete_user_cmd))

    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("configure", configure)],
            states={
                LANG: [CallbackQueryHandler(lang_handler)],
                LEVEL: [CallbackQueryHandler(level_handler)],
                TIMEZONE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, timezone_search_handler
                    ),
                    CallbackQueryHandler(timezone_choice_handler),
                ],
                TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_handler)],
                COMPLETE: [CallbackQueryHandler(complete_handler)],
                RECONFIRM: [CallbackQueryHandler(reconfirm_handler)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )
    restart_jobs(application.job_queue)
    application.run_polling()
