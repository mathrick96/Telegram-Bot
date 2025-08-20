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

# dummy_user = (358696654, 'thai', 'A2', '15:00:00', 1)

# # Avoid duplicate PK on re-runs
# cursor.execute(
#     "INSERT OR IGNORE INTO users (user_id, language, level, delivery_time, configured) VALUES (?, ?, ?, ?, ?)",
#     dummy_user
# )

# conn.commit()

# rows = cursor.execute("SELECT * FROM users").fetchall()

# helper functions for db interaction

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
                VALUES (?, ?, ?, ?, ?)
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

def update_user(user_data):
    try:
        user_id, language, level, delivery_time, configured = user_data
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE users
                   SET language = ?,
                       level = ?,
                       delivery_time = ?,
                       configured = ?
                 WHERE user_id = ?
            """, (language, level, delivery_time, configured, user_id))
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

# logging.info("\nUsers table rows: %s", rows) 
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


async def configure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # algoritmo
    # quando questo comando viene chiamato si inizia il processo di onboarding dell'user
    # 1) si crea una riga piena di NULL con solo l'user_id
    # 2) si chiede quale è la lingua scelta (tra una lista di lingue che devo preparare) e la si salva nel db
    # 3) si chiede quale sia il livello (salvandolo in uppercase e tra i sei possibili) e lo si salva nel db
    # 4) si chiede quale sia l'orario a in cui si vuole ricevere il testo (controllando che sia un'ora valida) e lo si salva nel db
    # 5) usare un branch per allenarsi su come si fa

    pass


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id = update.message.from_user.id
    text = update.message.text
    await update.message.reply_text(f"Your id: {id}, your message: {text}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(bot_key).build()
    
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    
    application.run_polling()