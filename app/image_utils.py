import numpy as np
import cv2
from PIL import Image
import logging
import io

logger = logging.getLogger(__name__)


def convert_yuv422_to_rgb(yuv422_data, width=160, height=120):
    """
    Convert YUV422 from ESP32-CAM to RGB using fast OpenCV C++ bindings.
    """
    try:
        # Validate size (160 * 120 * 2 = 38400 bytes for QQVGA)
        expected_size = width * height * 2
        if len(yuv422_data) != expected_size:
            logger.warning(
                f"Expected {expected_size} bytes but got {len(yuv422_data)}."
            )
            # Auto-detect resolution based on actual bytes received
            total_pixels = len(yuv422_data) // 2
            if total_pixels == 19200:
                width, height = 160, 120  # QQVGA (Your current Rust setting)
            elif total_pixels == 76800:
                width, height = 320, 240  # QVGA
            else:
                logger.error("Data size does not match known resolutions.")
                raise ValueError("Invalid image data size")

        # 1. Load raw bytes into a flat numpy array
        yuv_array = np.frombuffer(yuv422_data, dtype=np.uint8)

        # 2. Reshape it to what OpenCV expects: (Height, Width, 2 channels)
        yuv_reshaped = yuv_array.reshape((height, width, 2))

        # 3. Convert to RGB using OpenCV
        # THE FIX: We use UYVY instead of YUYV to fix the Green/Magenta ghosting.
        #rgb_image = cv2.cvtColor(yuv_reshaped, cv2.COLOR_YUV2RGB_UYVY)

        # NOTE: If the image STILL looks weird (or blue faces), comment out the line above
        # and uncomment the line below to try the other byte order:
        rgb_image = cv2.cvtColor(yuv_reshaped, cv2.COLOR_YUV2RGB_YUYV)

        return rgb_image

    except Exception as e:
        logger.error(f"Error converting YUV422 to RGB: {str(e)}")
        raise


def yuv_to_rgb(y, u, v):
    """
    Convert YUV to RGB using standard conversion formulas
    """
    # Convert to float for calculation
    y, u, v = float(y), float(u), float(v)

    # Standard YUV to RGB conversion
    r = y + 1.402 * (v - 128)
    g = y - 0.344136 * (u - 128) - 0.714136 * (v - 128)
    b = y + 1.772 * (u - 128)

    # Clamp values to 0-255 range
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))

    return r, g, b


def convert_to_jpeg(rgb_image, quality=85):
    """
    Convert RGB numpy array to JPEG bytes
    """
    try:
        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(rgb_image)

        # Convert to JPEG bytes
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format="JPEG", quality=quality)

        return img_byte_arr.getvalue()

    except Exception as e:
        logger.error(f"Error converting RGB to JPEG: {str(e)}")
        raise


def validate_image_format(data):
    """
    Attempt to validate if the image data is in a recognizable format
    """
    # Check if it starts with common image headers
    if len(data) < 10:
        return False, "Data too short"

    header = data[:10]

    # JPEG header
    if header[0] == 0xFF and header[1] == 0xD8:
        return True, "JPEG"

    # PNG header
    if header[0:8] == b"\x89PNG\r\n\x1a\n":
        return True, "PNG"

    # BMP header
    if header[0:2] == b"BM":
        return True, "BMP"

    # Raw YUV422 format doesn't have a header, so we'll assume it's raw if it's not a known format
    # and has the expected size for a common resolution
    expected_sizes = [
        160 * 120 * 2,  # QQVGA
        176 * 144 * 2,  # QCIF
        352 * 288 * 2,  # CIF
        640 * 480 * 2,  # VGA
    ]

    if len(data) in expected_sizes:
        return True, "RAW_YUV422"

    return False, "Unknown format"
