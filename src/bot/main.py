import logging, os
import sqlite3
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

DB_PATH = "/app/src/data/users.db"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def chunk(lst, n): 
        return [lst[i:i+n] for i in range(0, len(lst), n)]

dummy_user = (000000000, 'english', 'A1', '00:00:00')

load_dotenv()
bot_key = os.getenv("TELEGRAM_BOT_KEY")

with open("/app/src/bot/config.json") as f:
            cfg = json.load(f)

# database connection and table creation
conn = sqlite3.connect('/app/src/data/users.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    language TEXT,
    level TEXT,
    delivery_time TEXT,   
    configured INTEGER   
)
""")

conn.close()

######################################################################################
############################   HELPER FUNCTIONS   ####################################
######################################################################################

def log_all_users():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, language, level, delivery_time, configured
                FROM users
                ORDER BY user_id
            """)
            rows = cur.fetchall()
            logging.info("DB dump: %d row(s) in users.", len(rows))
            for r in rows:
                logging.info(
                    "user_id=%s | language=%s | level=%s | delivery_time=%s | configured=%s",
                    r["user_id"], r["language"], r["level"], r["delivery_time"], r["configured"]
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
            cur.execute("""
                INSERT OR IGNORE INTO users
                (user_id, configured)
                VALUES (?, 0)
            """, (user_id,))
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
            cur.execute("""
                INSERT OR IGNORE INTO users
                (user_id, language, level, delivery_time, configured)
                VALUES (?, ?, ?, ?, 1)
            """, user_data)
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

def update_user(user_id, language=None, level=None, delivery_time=None, configured=None):
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
    if configured is not None:
        fields.append("configured = ?")
        values.append(configured)
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
                logging.warning(f"No user found with user_id {user_id}. Update skipped.")
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
                logging.warning(f"No user found with user_id {user_id}. Deletion skipped.")
                return False
    except Exception as e:
        logging.error(f"Error deleting user_id {user_id}: {e}")
        return False


######################################################################################
############################   MESSAGES & COMMANDS   #################################
######################################################################################


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text = (
            "👋 Hello and welcome to Daily Language Boost\\!\n"
            "I’ll send you one short, level\\-appropriate text **every day** in the language you choose, plus a few follow\\-up questions to keep you thinking\\.\n"
            "**How to get started**\n"
            "Start with the command /configure and tell me the following data"
            "1️⃣  Your target language\n"
            "2️⃣  Your CEFR level in that language \\(A1–C2\\)\n"
            "3️⃣  The local time you’d like to receive each text"
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id = update.message.from_user.id
    text = update.message.text
    await update.message.reply_text(f"Your id: {id}, your message: {text}")



    # algoritmo
    # quando questo comando viene chiamato si inizia il processo di onboarding dell'user
    # 1) si crea una riga piena di NULL con solo l'user_id
    # 2) si chiede quale è la lingua scelta (tra una lista di lingue che devo preparare) e la si salva nel db
    # 3) si chiede quale sia il livello (salvandolo in uppercase e tra i sei possibili) e lo si salva nel db
    # 4) si chiede quale sia l'orario a in cui si vuole ricevere il testo (controllando che sia un'ora valida) e lo si salva nel db
    # 5) usare un branch per allenarsi su come si fa

LANG, LEVEL, TIME, COMPLETE = range(4)

async def configure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    "Starts the configuration and asks for the language"
    user_id = update.message.from_user.id
    create_new_user(user_id)
    items = list(cfg['languages'].items())
    rows = chunk(items, 3)
    kb = [[InlineKeyboardButton(l[0], callback_data=f'{l[1]}') for l in row] for row in rows]
     
    await update.message.reply_text("Hey there!\nPlease selelct the name of the language that you want to study or select /cancel to abort.\n",
                                    reply_markup=InlineKeyboardMarkup(kb))
    


    return LANG

async def lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = query.data 
    context.user_data["language"] = language
    update_user(query.from_user.id, language=language)
    levels = cfg['cefr_levels']
    rows = chunk(levels, 2)
    kb = [[InlineKeyboardButton(l, callback_data=f'{l}') for l in row] for row in rows]



    await query.edit_message_text(text=f"You chose {language}.\nNow select a level or type /cancel to abort",
                                           reply_markup=InlineKeyboardMarkup(kb))
    
    return LEVEL


async def level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data
    context.user_data["level"] = level
    update_user(query.from_user.id, level=level)
    await query.edit_message_text(text=f"You chose {level}.\nNow select a delivery time in the form HH:MM or type /cancel to abort")

    return TIME

async def time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    time = query.data
    context.user_data["time"] = time
    kb = [[InlineKeyboardButton('Ok', callback_data='ok')]]
    update_user(query.from_user.id, delivery_time=time)
    await query.edit_message_text(f"Setup complete!\nYou chose the following options:\nLanguage: {context.user_data["language"]}"
                                  f"\nLevel: {context.user_data["level"]}\nTime: {context.user_data["time"]}.1n"
                                  "If this is correct tap ok, if not type /cancel and start again.",
                                  reply_markup=InlineKeyboardMarkup(kb))
    return COMPLETE

async def complete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # here I want to react to the press of the OK button changing the status of configured to 1
    return ConversationHandler.END
    

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Conversation cancelled.")
    return ConversationHandler.END
######################################################################################
###############################   DIAGNOSTICS   ######################################
######################################################################################


async def insert_dummy_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    saved = save_new_user(dummy_user)
    if saved:
        await context.bot.send_message(chat_id=update.effective_chat.id, text = ('dummy user saved'))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text = ('error in saving dummy user'))

async def delete_dummy_user(update:Update, context: ContextTypes.DEFAULT_TYPE):
    deleted = delete_user(dummy_user[0])
    if deleted:
        await context.bot.send_message(chat_id=update.effective_chat.id, text = ('dummy user deleted'))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text = ('error in deleting dummy user'))

async def log_db_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = log_all_users()
    if n is None:
        await update.message.reply_text("DB dump failed. Check server logs.")
    else:
        await update.message.reply_text(f"Logged {n} row(s) to server logs.")


######################################################################################
##################################   MAIN    #########################################
######################################################################################


if __name__ == '__main__':
    application = ApplicationBuilder().token(bot_key).build()

    # message handler
    #application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    # diagnostics
    application.add_handler(CommandHandler('dummy', insert_dummy_user))
    application.add_handler(CommandHandler('deldummy', delete_dummy_user))
    application.add_handler(CommandHandler('logdb', log_db_cmd))

    # command handlers
    application.add_handler(CommandHandler('start', start))

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("configure", configure)],
        states={
            LANG: [CallbackQueryHandler(lang_handler)],   # handler for inline buttons
            LEVEL: [CallbackQueryHandler(level_handler)],
            TIME: [CallbackQueryHandler(time_handler)],
            COMPLETE: [CallbackQueryHandler(complete_handler)]
            },
        fallbacks=[CommandHandler("cancel", cancel)],
        )
    )



    
    application.run_polling()