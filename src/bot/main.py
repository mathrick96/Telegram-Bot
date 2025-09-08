import logging
import os
import sqlite3

from dotenv import load_dotenv



from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

from .paths import DATA_DIR, DB_PATH
from .db import migrate_last_sent_to_timestamp, ensure_paused_column
from .handlers import (
    start,
    stop,
    help,
    configure,
    lang_handler,
    level_handler,
    time_handler,
    timezone_button_handler,
    complete_handler,
    cancel,
    log_db_cmd,
    delete_user_cmd,

    LANG,
    LEVEL,
    TIME,
    COMPLETE,
    cfg,
)
from .scheduler import restart_jobs

# Load environment variables before importing modules that rely on them
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

bot_key = os.getenv("TELEGRAM_BOT_KEY")
if not bot_key:
    logging.critical("TELEGRAM_BOT_KEY is not set in environment variables")
    raise RuntimeError("Missing TELEGRAM_BOT_KEY environment variable")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# database connection and table creation
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        language TEXT,
        level TEXT,
        delivery_hour INTEGER,
        timezone TEXT,
        last_sent TEXT,
        configured INTEGER,
        paused INTEGER DEFAULT 0
    )
    """
)

conn.close()
migrate_last_sent_to_timestamp()
ensure_paused_column()


language_pattern = f"^({'|'.join(cfg['languages'].values())})$"
level_pattern = f"^({'|'.join(cfg['cefr_levels'])})$"


if __name__ == "__main__":
    application = ApplicationBuilder().token(bot_key).build()


    # diagnostics
    application.add_handler(CommandHandler("logdb", log_db_cmd))

    # command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("deleteuser", delete_user_cmd))
    # message handler (disabled)
    #application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("configure", configure)],
            states={
                LANG: [CallbackQueryHandler(lang_handler, pattern=language_pattern)],
                LEVEL: [CallbackQueryHandler(level_handler, pattern=level_pattern)],
                TIME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, time_handler),
                    CallbackQueryHandler(timezone_button_handler),
                ],
                COMPLETE: [CallbackQueryHandler(complete_handler)],
                },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    restart_jobs(application.job_queue)
    application.run_polling()
