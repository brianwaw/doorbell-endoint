import numpy as np
import cv2
from PIL import Image
import logging
import io

logger = logging.getLogger(__name__)

def convert_yuv422_to_rgb(yuv422_data, width=160, height=120):
    """
    Convert YUV422 packed format to RGB.
    
    YUV422 format stores data as U-Y-V-Y sequence, meaning:
    - Every 2 pixels share U and V values
    - Each pixel has its own Y value
    - Total bytes = width * height * 2 (since 2 bytes per pixel)
    
    Args:
        yuv422_data: Raw bytes from ESP32-CAM in YUV422 format
        width: Width of the image (default QQVGA 160)
        height: Height of the image (default QQVGA 120)
    
    Returns:
        RGB image as numpy array
    """
    try:
        # Validate input size
        expected_size = width * height * 2
        if len(yuv422_data) != expected_size:
            logger.warning(f"Expected {expected_size} bytes but got {len(yuv422_data)}. Trying to reshape...")
            # Try to determine dimensions from data size
            total_pixels = len(yuv422_data) // 2
            # Common QQVGA resolution is 160x120 = 19200 pixels
            if total_pixels == 19200:
                width, height = 160, 120
            elif total_pixels == 38400:  # QCIF
                width, height = 176, 144
            elif total_pixels == 76800:  # CIF
                width, height = 352, 288
            elif total_pixels == 921600:  # VGA
                width, height = 640, 480
            else:
                # Default to QQVGA
                width, height = 160, 120
            expected_size = width * height * 2
        
        # Reshape the data to (height, width*2) - each row contains interleaved UVY values
        yuv422_array = np.frombuffer(yuv422_data, dtype=np.uint8)
        yuv422_reshaped = yuv422_array.reshape((height, width * 2))
        
        # Create output arrays
        rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Process each row
        for i in range(height):
            # Process pairs of pixels (every 4 bytes represent 2 pixels: U0, Y0, V0, Y1)
            for j in range(0, width * 2, 4):
                if j + 3 < width * 2:
                    # First pixel: U0, Y0, V0, Y1
                    u = yuv422_reshaped[i, j]      # U value for both pixels
                    y0 = yuv422_reshaped[i, j + 1]  # Y value for first pixel
                    v = yuv422_reshaped[i, j + 2]   # V value for both pixels
                    y1 = yuv422_reshaped[i, j + 3]  # Y value for second pixel
                    
                    # Convert YUV to RGB for first pixel
                    r0, g0, b0 = yuv_to_rgb(y0, u, v)
                    # Convert YUV to RGB for second pixel
                    r1, g1, b1 = yuv_to_rgb(y1, u, v)
                    
                    # Assign to output image
                    x0 = j // 2
                    x1 = x0 + 1
                    
                    if x0 < width:
                        rgb_image[i, x0] = [r0, g0, b0]
                    if x1 < width:
                        rgb_image[i, x1] = [r1, g1, b1]
        
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
        pil_image.save(img_byte_arr, format='JPEG', quality=quality)
        
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
    if header[0:8] == b'\x89PNG\r\n\x1a\n':
        return True, "PNG"
    
    # BMP header
    if header[0:2] == b'BM':
        return True, "BMP"
    
    # Raw YUV422 format doesn't have a header, so we'll assume it's raw if it's not a known format
    # and has the expected size for a common resolution
    expected_sizes = [
        160 * 120 * 2,    # QQVGA
        176 * 144 * 2,    # QCIF
        352 * 288 * 2,    # CIF
        640 * 480 * 2,    # VGA
    ]
    
    if len(data) in expected_sizes:
        return True, "RAW_YUV422"
    
    return False, "Unknown format"
