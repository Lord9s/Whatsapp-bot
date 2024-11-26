import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
from flask_cors import CORS
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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "my_telegram_bot")
PREFIX = os.getenv("PREFIX", "/")

# Initialize Telegram bot
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Verify token validity
try:
    bot.get_me()  # Test the token by getting bot details
    logger.info("Telegram Bot Token is valid.")
except telegram.error.InvalidToken:
    logger.error("Invalid Telegram Token. Please check your token.")
    exit(1)  # Exit if token is invalid

# Start time tracking
start_time = time.time()


def get_bot_uptime():
    return time.time() - start_time


# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = update.effective_user
    logger.info(f"Received /start command from user: {user.username} ({user.id})")
    response = f"Hello, {user.first_name}! I am your bot, ready to assist you!"
    logger.info(f"Bot response: {response}")
    await update.message.reply_text(response)


async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /uptime command."""
    uptime = get_bot_uptime()
    response = f"I have been running for {uptime:.2f} seconds."
    logger.info(f"Received /uptime command. Bot response: {response}")
    await update.message.reply_text(response)


# Message Handlers
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages."""
    try:
        message = update.message.text
        user = update.effective_user
        logger.info(f"Received message from user {user.username} ({user.id}): {message}")

        if message.startswith(PREFIX):
            command = message[len(PREFIX):]
            response = messageHandler.handle_text_command(command)
        else:
            response = messageHandler.handle_text_message(message)

        logger.info(f"Bot response to user {user.username} ({user.id}): {response}")
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        await update.message.reply_text("🚨 An error occurred while processing your message.")


async def handle_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles attachments (e.g., images, files)."""
    try:
        user = update.effective_user
        if update.message.photo:
            # Get the largest available photo
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()

            logger.info(f"Received photo from user {user.username} ({user.id})")
            response = messageHandler.handle_attachment(photo_bytes, attachment_type="image")
        else:
            response = "Sorry, I cannot process this attachment type."

        logger.info(f"Bot response to user {user.username} ({user.id}): {response}")
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error handling attachment: {str(e)}")
        await update.message.reply_text("🚨 An error occurred while processing your attachment.")


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles unknown commands."""
    user = update.effective_user
    logger.warning(f"Unknown command received from user {user.username} ({user.id}): {update.message.text}")
    response = "Sorry, I didn't understand that command."
    logger.info(f"Bot response to user {user.username} ({user.id}): {response}")
    await update.message.reply_text(response)


# Initialize Telegram bot application
app_telegram = Application.builder().token(TELEGRAM_TOKEN).build()

# Add handlers to the bot
app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("uptime", uptime))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app_telegram.add_handler(MessageHandler(filters.PHOTO, handle_attachment))  # Handle attachments
app_telegram.add_handler(MessageHandler(filters.COMMAND, handle_unknown))


# Start the bot
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
