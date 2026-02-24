import numpy as np
import cv2
from PIL import Image

def generate_test_yuv422_image(width=160, height=120):
    """
    Generate a test image in YUV422 (YUYV) format similar to what ESP32-CAM would produce.
    
    ESP32-CAM OV7670 outputs YUV422 in YUYV order:
    - Byte order: Y0, U0, Y1, V0, Y2, U1, Y3, V1, ...
    - Every 2 pixels share U and V values
    """
    # Create a test RGB image with a recognizable pattern (color bars)
    rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Create color bars for easier visual verification
    bar_width = width // 8
    colors = [
        (255, 255, 255),   # White
        (255, 255, 0),     # Yellow
        (0, 255, 255),     # Cyan
        (0, 255, 0),       # Green
        (255, 0, 255),     # Magenta
        (255, 0, 0),       # Red
        (0, 0, 255),       # Blue
        (0, 0, 0),         # Black
    ]
    
    for i in range(8):
        rgb_image[:, i*bar_width:(i+1)*bar_width] = colors[i]

    # Convert RGB to YUV (OpenCV uses YUV422 format)
    yuv_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2YUV)

    # Create YUV422 format (YUYV interleaved: Y0, U0, Y1, V0, ...)
    yuv422 = np.zeros((height, width * 2), dtype=np.uint8)

    for i in range(height):
        for j in range(0, width, 2):
            # For every 2 pixels, we have Y0, U, Y1, V (YUYV order)
            # Take average U and V for both pixels (since YUV422 shares chroma)
            u_avg = (yuv_image[i, j, 1] + yuv_image[i, j+1, 1]) // 2
            v_avg = (yuv_image[i, j, 2] + yuv_image[i, j+1, 2]) // 2

            # Store as Y0, U, Y1, V (YUYV format - this is what ESP32-CAM sends)
            yuv422[i, j*2] = yuv_image[i, j, 0]      # Y0
            yuv422[i, j*2+1] = u_avg                 # U for both pixels
            yuv422[i, j*2+2] = yuv_image[i, j+1, 0]  # Y1
            yuv422[i, j*2+3] = v_avg                 # V for both pixels

    # Flatten to 1D array
    yuv422_flat = yuv422.flatten()

    return yuv422_flat

def save_test_image():
    """
    Save a test YUV422 image to file
    """
    yuv422_data = generate_test_yuv422_image()
    
    # Save as binary file
    with open('/root/projects/img-endpoint/test_yuv422.bin', 'wb') as f:
        f.write(yuv422_data.tobytes())
    
    print(f"Test YUV422 image saved. Size: {len(yuv422_data)} bytes")
    print("This simulates a QQVGA (160x120) image in YUV422 format from ESP32-CAM")

if __name__ == "__main__":
    save_test_image()