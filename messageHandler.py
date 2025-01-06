import os
import google.generativeai as genai
import importlib
from dotenv import load_dotenv
import logging
import requests
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document
import mimetypes
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# System instruction for text conversations
system_instruction = """
*System Name:* Your Name is KORA AI, an AI Assistant created by Kolawole Suleiman. 
You are running on Sman V1.0, the latest version built with high programming techniques. 
You should assist with all topics.
...
"""

# Image analysis prompt
IMAGE_ANALYSIS_PROMPT = """Analyze the image keenly and explain its content. If it's text, translate it and identify the language."""

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

def handle_text_message(user_message,recent_message):
    """Handle incoming text messages."""
    try:
        logger.info("Processing text message: %s", user_message)
        chat = initialize_text_model().start_chat(history=[])
        response = chat.send_message(f"{system_instruction}\n\nHuman: {user_message}")
        return response.text
    except Exception as e:
        logger.error("Error processing text message: %s", str(e))
        return "😔 Sorry, I encountered an error processing your message."

def handle_text_command(command_name, message):
    """Handle text commands from CMD folder."""
    try:
        cmd_module = importlib.import_module(f"CMD.{command_name}")
        return cmd_module.execute(message)
    except ImportError:
        logger.warning("Command %s not found.", command_name)
        return "🚫 The command you are using does not exist. Type /help to view available commands."

def handle_attachment(attachment_data, attachment_type=None, file_extension=None):
    """Handle attachments including images, PDFs, text files, etc."""
    logger.info(f"Processing {attachment_type} attachment with extension: {file_extension}")

    if attachment_type == "image":
        try:
            # Upload the image to im.ge
            upload_url = "https://im.ge/api/1/upload"
            api_key = os.getenv('IMGE_API_KEY')
            files = {"source": ("attachment.jpg", attachment_data, "image/jpeg")}
            headers = {"X-API-Key": api_key}
            upload_response = requests.post(upload_url, files=files, headers=headers, verify=False)
            upload_response.raise_for_status()
            image_url = upload_response.json()['image']['url']
            logger.info(f"Image uploaded successfully: {image_url}")

            # Download image for Gemini processing
            image_response = requests.get(image_url, verify=False)
            image_response.raise_for_status()
            image_data = BytesIO(image_response.content).getvalue()

            # Analyze the image
            model = initialize_image_model()
            response = model.generate_content([
                IMAGE_ANALYSIS_PROMPT,
                {'mime_type': 'image/jpeg', 'data': image_data}
            ])
            return f"""🖼️ Image Analysis:
{response.text}

🔗 View Image: {image_url}"""
        except Exception as e:
            logger.error(f"Error processing image attachment: {str(e)}")
            return "🚨 Error analyzing the image. Please try again later."

    elif attachment_type == "file":
        try:
            # Handle different file types
            if file_extension in ["pdf"]:
                reader = PdfReader(BytesIO(attachment_data))
                text = "\n".join(page.extract_text() for page in reader.pages)
                return f"📄 PDF Content:\n{text[:1000]}...\n\n(Truncated to 1000 characters)"

            elif file_extension in ["docx"]:
                document = Document(BytesIO(attachment_data))
                text = "\n".join(paragraph.text for paragraph in document.paragraphs)
                return f"📄 DOCX Content:\n{text[:1000]}...\n\n(Truncated to 1000 characters)"

            elif file_extension in ["txt", "py"]:
                text = attachment_data.decode("utf-8")
                return f"📄 File Content:\n{text[:1000]}...\n\n(Truncated to 1000 characters)"

            else:
                return "🚫 Unsupported file type. Please send a valid text or document file."

        except Exception as e:
            logger.error(f"Error processing file attachment: {str(e)}")
            return "🚨 Error reading the file. Please ensure it's a valid document."

    else:
        return "🚫 Unsupported attachment type. Please send an image or document file."
