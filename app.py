import os
import logging
import time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

import messageHandler  # Import the message handler module

# Load environment variables
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PREFIX = os.getenv("PREFIX", "/")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

start_time = time.time()

# Expose the start_time so CMD can access it
def get_bot_uptime():
    return time.time() - start_time

# Helper function to format uptime
def format_duration(seconds):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

# Start command handler
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hey buddy 😁, I am KORA AI HOW CAN I HELP YOU ?")

# Uptime command handler
def uptime(update: Update, context: CallbackContext):
    uptime_seconds = get_bot_uptime()
    uptime_str = format_duration(uptime_seconds)
    update.message.reply_text(f"🤖 Bot Uptime: {uptime_str}")

# Message handler for text commands
def handle_text_command(update: Update, context: CallbackContext):
    message_text = update.message.text
    if message_text.startswith(PREFIX):
        command = message_text[len(PREFIX):]
        response = messageHandler.handle_text_command(command)
        update.message.reply_text(response)
    else:
        update.message.reply_text("🚫 Sorry, I didn't recognize that command type /help for Available Command.")

# Message handler for general text
def handle_text_message(update: Update, context: CallbackContext):
    message_text = update.message.text
    response = messageHandler.handle_text_message(message_text)
    update.message.reply_text(response)

# Handler for unknown commands
def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text("🚫 The Command you are using does not exist type /help to view Available Command.")

def main():
    # Initialize the Updater and Dispatcher
    updater = Updater(token=TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("uptime", uptime))

    # Message handlers
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text_message))
    dispatcher.add_handler(MessageHandler(Filters.command, handle_text_command))

    # Unknown command handler
    dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

    # Start the bot
    updater.start_polling()
    logger.info("Bot is running...")
    updater.idle()

if __name__ == "__main__":
    main()
