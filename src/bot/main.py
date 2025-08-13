import logging, os
import sqlite3
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode


load_dotenv()
bot_key = os.getenv("TELEGRAM_BOT_KEY")

# database connection 
conn = sqlite3.connect('/app/src/data/users.db')


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


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


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


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