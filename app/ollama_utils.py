import os
import requests
import base64
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Ollama configuration - can be overridden via environment variable
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:cloud")


def image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string for Ollama API."""
    return base64.b64encode(image_bytes).decode('utf-8')


def is_image_worth_sending(image_bytes: bytes) -> Tuple[bool, str]:
    """
    Use Ollama to analyze if an image is worth sending to Telegram.

    Returns a tuple of (is_worth_sending: bool, reason: str).
    The reason explains why the model chose the response it did.
    """
    try:
        # Convert image to base64
        base64_image = image_to_base64(image_bytes)

        # Prompt that instructs Ollama to analyze the image content
        prompt = (
            "Analyze this image carefully. "
            "Only respond with 'YES' if the image contains a person or something important that warrants a doorbell notification. "
            "Respond with 'NO' if the image is empty, contains only meaningless objects like furniture, walls, or is just a random object without people. "
            "After your YES or NO response, on a new line, provide a brief reason (1-2 sentences) explaining your decision."
        )

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "images": [base64_image],
            "stream": False
        }

        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)

        if response.status_code != 200:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            # Fail safe: allow image if Ollama is unavailable
            return True, f"Ollama API error: {response.status_code}"

        result = response.json()
        response_text = result.get('response', '').strip()

        logger.info(f"Ollama analysis result: {response_text}")

        # Parse the response to extract YES/NO and reason
        lines = response_text.split('\n')
        first_line = lines[0].strip().upper()

        is_worth_sending = first_line.startswith('YES')

        # The reason is everything after the first line
        if len(lines) > 1:
            reason = ' '.join(line.strip() for line in lines[1:] if line.strip())
        else:
            reason = response_text if not is_worth_sending else "Image appears to contain something worth notifying"

        return is_worth_sending, reason

    except requests.exceptions.ConnectionError:
        logger.warning("Could not connect to Ollama - allowing image through")
        # Fail safe: allow image if Ollama is unavailable
        return True, "Could not connect to Ollama"
    except requests.exceptions.Timeout:
        logger.warning("Ollama request timed out - allowing image through")
        return True, "Ollama request timed out"
    except Exception as e:
        logger.error(f"Error analyzing image with Ollama: {str(e)}")
        # Fail safe: allow image if analysis fails
        return True, f"Error analyzing image: {str(e)}"


def filter_image_before_sending(image_bytes: bytes) -> Tuple[bool, str]:
    """
    Wrapper function to check if image passes the Ollama filter.

    Returns a tuple of (should_send: bool, reason: str).
    """
    return is_image_worth_sending(image_bytes)
