import numpy as np
import cv2
from PIL import Image

def generate_test_yuv422_image(width=160, height=120):
    """
    Generate a test image in YUV422 format similar to what ESP32-CAM would produce
    """
    # Create a test RGB image
    rgb_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    # Convert RGB to YUV
    yuv_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2YUV)
    
    # Create YUV422 format (interleaved U-Y-V-Y)
    yuv422 = np.zeros((height, width * 2), dtype=np.uint8)
    
    for i in range(height):
        for j in range(0, width, 2):
            # For every 2 pixels, we have U0, Y0, V0, Y1
            # Take average U and V for both pixels (since YUV422 shares chroma)
            u_avg = (yuv_image[i, j, 1] + yuv_image[i, j+1, 1]) // 2
            v_avg = (yuv_image[i, j, 2] + yuv_image[i, j+1, 2]) // 2
            
            # Store as U0, Y0, V0, Y1 (interleaved format)
            yuv422[i, j*2] = u_avg      # U for both pixels
            yuv422[i, j*2+1] = yuv_image[i, j, 0]    # Y0
            yuv422[i, j*2+2] = v_avg    # V for both pixels
            yuv422[i, j*2+3] = yuv_image[i, j+1, 0]  # Y1
    
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