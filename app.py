import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
import requests
import messageHandler  # Import your custom message handler module
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PREFIX = os.getenv("PREFIX", "/")

# Verification endpoint for WhatsApp webhook
@app.route('/webhook', methods=['GET'])
def verify():
    token_sent = request.args.get("hub.verify_token")
    if token_sent == VERIFY_TOKEN:
        logger.info("Webhook verification successful.")
        return request.args.get("hub.challenge")
    logger.error("Webhook verification failed: invalid verify token.")
    return "Verification failed", 403

# Main webhook endpoint to handle messages
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    logger.info("Received data: %s", data)

    # Check if the webhook is from WhatsApp
    if data.get("object") == "whatsapp_business_account":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for message in messages:
                    sender_id = message["from"]
                    message_text = message.get("text", {}).get("body")
                    message_type = message.get("type")
                    message_command = message_text if message_text and message_text.startswith(PREFIX) else None

                    # Check if message has text with a command prefix
                    if message_command:
                        response = messageHandler.handle_text_command(message_command[len(PREFIX):])
                    elif message_type == "image" or message_type == "video" or message_type == "document":
                        response = messageHandler.handle_attachment(message)
                    elif message_text:
                        response = messageHandler.handle_text_message(message_text)
                    else:
                        response = "Sorry, I didn't understand that message."

                    # Send the response to the user on WhatsApp
                    send_message(sender_id, response)
    return "EVENT_RECEIVED", 200

# Send message back to WhatsApp
def send_message(recipient_id, message_text):
    url = "https://graph.facebook.com/v15.0/{phone_number_id}/messages"
    params = {"access_token": WHATSAPP_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": message_text}
    }
    
    response = requests.post(url, headers=headers, params=params, json=data)
    
    if response.status_code == 200:
        logger.info("Message sent successfully to user %s", recipient_id)
    else:
        logger.error("Failed to send message: %s", response.json())

# Test WhatsApp token validity
@app.before_request
def check_whatsapp_token():
    test_url = f"https://graph.facebook.com/v15.0/me?access_token={WHATSAPP_TOKEN}"
    response = requests.get(test_url)
    if response.status_code == 200:
        logger.info("WhatsApp token is valid.")
    else:
        logger.error("Invalid WhatsApp token: %s", response.json())

start_time = time.time()

# Expose the start_time so CMD can access it
def get_bot_uptime():
    return time.time() - start_time

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
