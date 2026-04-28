from fastapi import FastAPI, UploadFile, File, HTTPException, Request
import numpy as np
import cv2
import io
import requests
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from PIL import Image
import uvicorn
from pydantic import BaseModel
from typing import Optional
import os

# Import our custom image processing utilities
from image_utils import convert_yuv422_to_rgb, convert_to_jpeg, validate_image_format
from ollama_utils import filter_image_before_sending

app = FastAPI(title="ESP32-CAM Image Processor", description="API to receive images from ESP32-CAM and send to Telegram")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/doorbell.db")


def get_db_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with the images table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            image_data BLOB NOT NULL,
            was_sent INTEGER NOT NULL,
            llm_reason TEXT NOT NULL,
            format_type TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_image_to_db(image_id: str, image_data: bytes, was_sent: bool, llm_reason: str, format_type: Optional[str] = None):
    """Save an image to the database with its metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO images (id, timestamp, image_data, was_sent, llm_reason, format_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (image_id, datetime.now(timezone.utc).isoformat(), image_data, 1 if was_sent else 0, llm_reason, format_type))
    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


class DoorbellRequest(BaseModel):
    message: Optional[str] = "There is someone at the door!"
    chat_id: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "ESP32-CAM Image Processing API is running!"}

@app.post("/doorbell/")
async def receive_image_from_esp32(
    request: Request
):
    """
    Receive image from ESP32-CAM, convert from YUV422 to JPEG, and send to Telegram.
    Images are always saved to database regardless of whether they are sent.
    """
    image_id = str(uuid.uuid4())
    try:
        # Read raw body from request
        contents = await request.body()

        # Validate the image format
        is_valid, format_type = validate_image_format(contents)

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {format_type}")

        # Process based on detected format
        if format_type == "RAW_YUV422":
            # Convert YUV422 to RGB
            rgb_image = convert_yuv422_to_rgb(contents)
        else:
            # Handle standard image formats (JPEG, PNG, etc.)
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("Could not decode image from provided data")

            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Convert RGB image to JPEG
        jpeg_bytes = convert_to_jpeg(rgb_image, quality=85)

        # Filter image using Ollama before sending - now returns (bool, reason)
        should_send, llm_reason = filter_image_before_sending(jpeg_bytes)

        # Always save to database regardless of whether it will be sent
        save_image_to_db(image_id, jpeg_bytes, should_send, llm_reason, format_type)
        logger.info(f"Image {image_id} saved to database - sent: {should_send}, reason: {llm_reason}")

        if not should_send:
            logger.info("Image filtered out by Ollama - not sending to Telegram")
            return {"status": "filtered", "message": "Image did not contain anything worth sending", "image_id": image_id}

        # Send to Telegram
        message = f"There is someone at the door!\n\nReason: {llm_reason}"
        chat_id = TELEGRAM_CHAT_ID

        if not TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=500, detail="Telegram bot token not configured")

        if not chat_id:
            raise HTTPException(status_code=500, detail="Telegram chat ID not configured")

        success = await send_to_telegram(jpeg_bytes, message, chat_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send image to Telegram")

        logger.info(f"Image processed and sent to Telegram successfully for chat_id: {chat_id}")

        return {"status": "success", "message": "Image received, processed, and sent to Telegram", "image_id": image_id}

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/doorbell_simple/")
async def receive_image_simple(image: UploadFile = File(...)):
    """
    Simple endpoint to receive image from ESP32-CAM and send to Telegram.
    This assumes the image is already in a standard format (JPEG, PNG, etc.).
    Images are always saved to database regardless of whether they are sent.
    """
    image_id = str(uuid.uuid4())
    try:
        # Read the uploaded image
        contents = await image.read()

        # Try to decode as is (assuming it's already in a standard format)
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image. Format may be unsupported.")

        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Convert to PIL Image and then to JPEG
        pil_img = Image.fromarray(rgb_image)
        img_byte_arr = io.BytesIO()
        pil_img.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr.seek(0)
        jpeg_bytes = img_byte_arr.getvalue()

        # Filter image using Ollama before sending - now returns (bool, reason)
        should_send, llm_reason = filter_image_before_sending(jpeg_bytes)

        # Always save to database regardless of whether it will be sent
        save_image_to_db(image_id, jpeg_bytes, should_send, llm_reason, "STANDARD")
        logger.info(f"Image {image_id} saved to database - sent: {should_send}, reason: {llm_reason}")

        if not should_send:
            logger.info("Image filtered out by Ollama - not sending to Telegram")
            return {"status": "filtered", "message": "Image did not contain anything worth sending", "image_id": image_id}

        # Send to Telegram
        message = f"There is someone at the door!\n\nReason: {llm_reason}"

        if not TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=500, detail="Telegram bot token not configured")

        if not TELEGRAM_CHAT_ID:
            raise HTTPException(status_code=500, detail="Telegram chat ID not configured")

        success = await send_to_telegram(jpeg_bytes, message, TELEGRAM_CHAT_ID)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send image to Telegram")

        logger.info("Simple image processed and sent to Telegram successfully")

        return {"status": "success", "message": "Image received, processed, and sent to Telegram", "image_id": image_id}

    except Exception as e:
        logger.error(f"Error processing simple image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


async def send_to_telegram(image_bytes: bytes, message: str, chat_id: str):
    """
    Send image and message to Telegram using Bot API
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

        # Prepare the file
        files = {'photo': ('image.jpg', image_bytes, 'image/jpeg')}
        data = {'chat_id': chat_id, 'caption': message}

        response = requests.post(url, files=files, data=data)

        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.text}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error sending to Telegram: {str(e)}")
        return False


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
