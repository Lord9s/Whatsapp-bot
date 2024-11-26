import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
from flask_cors import CORS
import asyncio
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import messageHandler  # Import the message handler module
import time

# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "my_telegram_bot")
PREFIX = os.getenv("PREFIX", "/")

# Initialize Telegram bot
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Validate the token asynchronously
async def validate_token():
    try:
        await bot.get_me()  # Test the token by getting bot details
        logger.info("Telegram Bot Token is valid.")
    except telegram.error.InvalidToken:
        logger.error("Invalid Telegram Token. Please check your token.")
        exit(1)  # Exit if the token is invalid

# Run token validation
asyncio.run(validate_token())

# Start time tracking
start_time = time.time()

def get_bot_uptime():
    return time.time() - start_time

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = update.effective_user
    logger.info(f"User message: {update.message.text}")
    response = f"Hello, {user.first_name}! I am your bot, ready to assist you!"
    logger.info(f"Bot response: {response}")
    await update.message.reply_text(response)

async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /uptime command."""
    logger.info(f"User message: {update.message.text}")
    uptime = get_bot_uptime()
    response = f"I have been running for {uptime:.2f} seconds."
    logger.info(f"Bot response: {response}")
    await update.message.reply_text(response)

# Message Handlers
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages."""
    message = update.message.text
    logger.info(f"User message: {message}")

    # Check if message is a command
    if message.startswith(PREFIX):
        command = message[len(PREFIX):]
        response = messageHandler.handle_text_command(command)
    else:
        response = messageHandler.handle_text_message(message)

    logger.info(f"Bot response: {response}")
    await update.message.reply_text(response)

async def handle_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles attachments (e.g., images, files)."""
    if update.message.photo:
        logger.info("User sent a photo.")
        response = messageHandler.handle_attachment(update.message.photo)
    else:
        response = "Sorry, I cannot process this attachment type."

    logger.info(f"Bot response: {response}")
    await update.message.reply_text(response)

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles unknown commands."""
    logger.info(f"User message: {update.message.text}")
    response = "Sorry, I didn't understand that command."
    logger.info(f"Bot response: {response}")
    await update.message.reply_text(response)

# Initialize Telegram bot application
app_telegram = Application.builder().token(TELEGRAM_TOKEN).build()

# Add handlers to the bot
app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("uptime", uptime))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app_telegram.add_handler(MessageHandler(filters.PHOTO, handle_attachment))  # Handle attachments
app_telegram.add_handler(MessageHandler(filters.COMMAND, handle_unknown))

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=3000)
