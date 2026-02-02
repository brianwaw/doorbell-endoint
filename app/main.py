from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
import numpy as np
import cv2
import io
import requests
import asyncio
import logging
from PIL import Image
import uvicorn
from pydantic import BaseModel
from typing import Optional
import os

# Import our custom image processing utilities
from image_utils import convert_yuv422_to_rgb, convert_to_jpeg, validate_image_format

app = FastAPI(title="ESP32-CAM Image Processor", description="API to receive images from ESP32-CAM and send to Telegram")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class DoorbellRequest(BaseModel):
    message: Optional[str] = "There is someone at the door!"
    chat_id: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "ESP32-CAM Image Processing API is running!"}

@app.post("/doorbell/")
async def receive_image_from_esp32(
    request: Request  # Changed to receive raw body
):
    """
    Receive image from ESP32-CAM, convert from YUV422 to JPEG, and send to Telegram
    """
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

        # Send to Telegram
        message = "There is someone at the door!"
        chat_id = TELEGRAM_CHAT_ID

        if not TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=500, detail="Telegram bot token not configured")

        if not chat_id:
            raise HTTPException(status_code=500, detail="Telegram chat ID not configured")

        success = await send_to_telegram(jpeg_bytes, message, chat_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send image to Telegram")

        logger.info(f"Image processed and sent to Telegram successfully for chat_id: {chat_id}")

        return {"status": "success", "message": "Image received, processed, and sent to Telegram"}

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


# Also keep the original file upload endpoint for compatibility
@app.post("/doorbell/upload/")
async def receive_image_upload(
    image: UploadFile = File(...),
    request_data: DoorbellRequest = None
):
    """
    Receive image from ESP32-CAM as file upload, convert from YUV422 to JPEG, and send to Telegram
    """
    try:
        # Read the uploaded image
        contents = await image.read()

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

        # Send to Telegram
        message = request_data.message if request_data else "There is someone at the door!"
        chat_id = request_data.chat_id if request_data and request_data.chat_id else TELEGRAM_CHAT_ID

        if not TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=500, detail="Telegram bot token not configured")

        if not chat_id:
            raise HTTPException(status_code=500, detail="Telegram chat ID not configured")

        success = await send_to_telegram(jpeg_bytes, message, chat_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send image to Telegram")

        logger.info(f"Image processed and sent to Telegram successfully for chat_id: {chat_id}")

        return {"status": "success", "message": "Image received, processed, and sent to Telegram"}

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/doorbell_simple/")
async def receive_image_simple(image: UploadFile = File(...)):
    """
    Simple endpoint to receive image from ESP32-CAM and send to Telegram
    This assumes the image is already in a standard format (JPEG, PNG, etc.)
    """
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
        
        # Send to Telegram
        message = "There is someone at the door!"
        
        if not TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=500, detail="Telegram bot token not configured")
        
        if not TELEGRAM_CHAT_ID:
            raise HTTPException(status_code=500, detail="Telegram chat ID not configured")
        
        success = await send_to_telegram(img_byte_arr.getvalue(), message, TELEGRAM_CHAT_ID)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send image to Telegram")
        
        logger.info("Simple image processed and sent to Telegram successfully")
        
        return {"status": "success", "message": "Image received, processed, and sent to Telegram"}
    
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
