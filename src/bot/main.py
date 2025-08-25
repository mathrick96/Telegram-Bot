import logging, os
import sqlite3
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

DB_PATH = "/app/src/data/users.db"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

dummy_user = (000000000, 'english', 'A1', '00:00:00')

load_dotenv()
bot_key = os.getenv("TELEGRAM_BOT_KEY")

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
            "1️⃣  Choose your target language\n"
            "2️⃣  Pick your CEFR level \\(A1–C2\\)\n"
            "3️⃣  Tell me the local time you’d like to receive each lesson"
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id = update.message.from_user.id
    text = update.message.text
    await update.message.reply_text(f"Your id: {id}, your message: {text}")


async def configure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id



    # algoritmo
    # quando questo comando viene chiamato si inizia il processo di onboarding dell'user
    # 1) si crea una riga piena di NULL con solo l'user_id
    # 2) si chiede quale è la lingua scelta (tra una lista di lingue che devo preparare) e la si salva nel db
    # 3) si chiede quale sia il livello (salvandolo in uppercase e tra i sei possibili) e lo si salva nel db
    # 4) si chiede quale sia l'orario a in cui si vuole ricevere il testo (controllando che sia un'ora valida) e lo si salva nel db
    # 5) usare un branch per allenarsi su come si fa

    pass

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    # diagnostics
    application.add_handler(CommandHandler('dummy', insert_dummy_user))
    application.add_handler(CommandHandler('deldummy', delete_dummy_user))
    application.add_handler(CommandHandler('logdb', log_db_cmd))

    # command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('configure', configure))



    
    application.run_polling()