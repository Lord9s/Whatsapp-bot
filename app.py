import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
import requests
import messageHandler  # Import your message handler module
import time
import sqlite3
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PREFIX = os.getenv("PREFIX", "/")

# SQLite Database Initialization
DB_PATH = "messages.db"

def init_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

def save_message(sender_id, message):
    """Save a message to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender_id, message) VALUES (?, ?)", (sender_id, message))
        conn.commit()

def get_recent_messages(sender_id):
    """Retrieve messages from the past 24 hours for a specific sender."""
    cutoff_time = datetime.now() - timedelta(hours=24)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message FROM messages 
            WHERE sender_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (sender_id, cutoff_time))
        return [row[0] for row in cursor.fetchall()]

def cleanup_old_messages():
    """Delete messages older than 24 hours."""
    cutoff_time = datetime.now() - timedelta(hours=24)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff_time,))
        conn.commit()

# Function to split long messages into chunks
def split_message(message, limit=4096):
    """Split a message into chunks within the WhatsApp character limit."""
    return [message[i:i+limit] for i in range(0, len(message), limit)]

# Function to send WhatsApp messages
def send_whatsapp_message(recipient_id, message):
    url = f"https://graph.facebook.com/v16.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json",
    }

    if isinstance(message, dict):  # Media or structured message
        payload = message
    else:  # Text message
        # Split long messages into chunks
        message_chunks = split_message(message)
        for chunk in message_chunks:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "text",
                "text": {"body": chunk},
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error("Failed to send message: %s", response.json())
                break

# Handle attachments (image, audio, etc.)
def send_media_message(recipient_id, media_type, media_url):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": media_type,
        media_type: {
            "link": media_url
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.info(f"{media_type.capitalize()} message sent successfully to {recipient_id}")
    else:
        logger.error("Failed to send media message: %s", response.json())

# Webhook verification for WhatsApp
@app.route('/webhook', methods=['GET'])
def verify():
    token_sent = request.args.get("hub.verify_token")
    if token_sent == VERIFY_TOKEN:
        logger.info("Webhook verification successful.")
        return request.args.get("hub.challenge", "")
    logger.error("Webhook verification failed: invalid verify token.")
    return "Verification failed", 403

# Main webhook endpoint to handle WhatsApp messages
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    logger.info("Received data: %s", data)

    cleanup_old_messages()  # Clean up old messages on every new message

    if data.get("object") == "whatsapp_business_account":
        for entry in data["entry"]:
            for change in entry["changes"]:
                if "messages" in change["value"]:
                    for message in change["value"]["messages"]:
                        recipient_id = message["from"]
                        message_type = message.get("type")
                        message_text = message.get("text", {}).get("body")
                        message_command = message_text if message_text and message_text.startswith(PREFIX) else None

                        # Save the message to the database
                        if message_text:
                            save_message(recipient_id, message_text)

                        # Handle text commands
                        if message_command:
                            sliced_message = message_command[len(PREFIX):]
                            command_name = sliced_message.split()[0]
                            command_message = sliced_message[len(command_name):].strip()

                            response = messageHandler.handle_text_command(command_name, message)
                            send_whatsapp_message(recipient_id, response["data"] if response.get("success") else "⚠️ Error processing your command.")

                        # Handle regular text messages
                        elif message_type == "text":
                            recent_messages = get_recent_messages(recipient_id)
                            bot_response = messageHandler.handle_text_message(message_text, recent_messages)
                            send_whatsapp_message(recipient_id, bot_response)

                        # Handle media attachments
                        elif message_type in ["image", "audio", "video", "document"]:
                            media_url = message[message_type]["url"]
                            response = messageHandler.handle_attachment(media_url, message_type)
                            send_whatsapp_message(recipient_id, response)
    return "EVENT_RECEIVED", 200

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
