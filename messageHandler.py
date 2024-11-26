import os
import google.generativeai as genai
import importlib
from dotenv import load_dotenv
import logging
import requests
from io import BytesIO
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# System instruction for text conversations
system_instruction = """
*System Name:* Your Name is KORA AI...
... [System instructions truncated for brevity]
"""

IMAGE_ANALYSIS_PROMPT = "Analyze the image keenly and explain its content."


def initialize_text_model():
    """Initialize Gemini model for text processing."""
    genai.configure(api_key=os.getenv("GEMINI_TEXT_API_KEY"))
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={
            "temperature": 0.3,
            "top_p": 0.95,
            "top_k": 30,
            "max_output_tokens": 8192,
        }
    )


def initialize_image_model():
    """Initialize Gemini model for image processing."""
    genai.configure(api_key=os.getenv("GEMINI_IMAGE_API_KEY"))
    return genai.GenerativeModel("gemini-1.5-pro")


def handle_text_message(user_message):
    try:
        logger.info(f"Processing text message: {user_message}")
        chat = initialize_text_model().start_chat(history=[])
        response = chat.send_message(f"{system_instruction}\n\nHuman: {user_message}")
        logger.info(f"Generated response: {response.text}")
        return response.text
    except Exception as e:
        logger.error(f"Error processing text message: {str(e)}")
        return "😔 Sorry, I encountered an error processing your message."


def handle_text_command(command_name):
    try:
        logger.info(f"Processing command: {command_name}")
        cmd_module = importlib.import_module(f"CMD.{command_name}")
        response = cmd_module.execute()
        logger.info(f"Command response: {response}")
        return response
    except ImportError:
        logger.warning(f"Command not found: {command_name}")
        return "🚫 The Command you are using does not exist, Type /help to view Available Commands."


def handle_attachment(attachment_data, attachment_type="image"):
    if attachment_type != "image":
        return "🚫 Unsupported attachment type. Please send an image."

    logger.info("Processing image attachment.")
    try:
        upload_url = "https://im.ge/api/1/upload"
        api_key = os.getenv('IMGE_API_KEY')

        files = {"source": ("attachment.jpg", attachment_data, "image/jpeg")}
        headers = {"X-API-Key": api_key}

        upload_response = requests.post(upload_url, files=files, headers=headers, verify=False)
        upload_response.raise_for_status()
        image_url = upload_response.json()['image']['url']
        logger.info(f"Image uploaded successfully: {image_url}")

        image_response = requests.get(image_url, verify=False)
        image_response.raise_for_status()
        image_data = BytesIO(image_response.content).getvalue()

        model = initialize_image_model()
        response = model.generate_content([
            IMAGE_ANALYSIS_PROMPT,
            {'mime_type': 'image/jpeg', 'data': image_data}
        ])

        logger.info(f"Image analysis response: {response.text}")
        return f"""🖼️ Image Analysis:
{response.text}

🔗 View Image: {image_url}"""
    except requests.RequestException as e:
        logger.error(f"Image upload/download error: {str(e)}")
        return "🚨 Error processing the image. Please try again later."
    except Exception as e:
        logger.error(f"Image analysis error: {str(e)}")
        return "🚨 Error analyzing the image. Please try again later."
