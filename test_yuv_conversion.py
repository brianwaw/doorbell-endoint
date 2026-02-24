#!/usr/bin/env python3
"""
Test script to verify YUV422 (YUYV) to JPEG conversion.
This simulates what the ESP32-CAM sends and verifies the conversion produces correct colors.
"""
import numpy as np
import cv2
from PIL import Image
import io

def yuv_to_rgb(y, u, v):
    """Convert YUV to RGB using standard conversion formulas"""
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


def convert_yuv422_to_rgb(yuv422_data, width=160, height=120):
    """
    Convert YUV422 packed format (YUYV order) to RGB.
    ESP32-CAM OV7670 outputs YUV422 in YUYV format: Y0, U0, Y1, V0, ...
    """
    yuv422_array = np.frombuffer(yuv422_data, dtype=np.uint8)
    yuv422_reshaped = yuv422_array.reshape((height, width * 2))
    
    rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    for i in range(height):
        for j in range(0, width * 2, 4):
            if j + 3 < width * 2:
                # YUYV format: Y0, U0, Y1, V0
                y0 = yuv422_reshaped[i, j]
                u = yuv422_reshaped[i, j + 1]
                y1 = yuv422_reshaped[i, j + 2]
                v = yuv422_reshaped[i, j + 3]
                
                r0, g0, b0 = yuv_to_rgb(y0, u, v)
                r1, g1, b1 = yuv_to_rgb(y1, u, v)
                
                x0 = j // 2
                x1 = x0 + 1
                
                if x0 < width:
                    rgb_image[i, x0] = [r0, g0, b0]
                if x1 < width:
                    rgb_image[i, x1] = [r1, g1, b1]
    
    return rgb_image


def generate_color_bar_yuv422(width=160, height=120):
    """Generate YUV422 data with color bars for testing using BT.601 YCrCb (JPEG standard)"""
    rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
    
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
    
    # Convert RGB to YCrCb using OpenCV (this matches the JPEG standard used in yuv_to_rgb)
    # OpenCV's YCrCb: Y = 0.299R + 0.587G + 0.114B
    #                 Cr = 0.713(R - Y) + 128 = 0.5R - 0.4187G - 0.0813B + 128
    #                 Cb = 0.564(B - Y) + 128 = -0.1687R - 0.3313G + 0.5B + 128
    ycrcb_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2YCrCb)
    
    yuv422 = np.zeros((height, width * 2), dtype=np.uint8)
    
    for i in range(height):
        for j in range(0, width, 2):
            # Cr is channel 2 (V), Cb is channel 1 (U)
            cb_avg = (ycrcb_image[i, j, 1] + ycrcb_image[i, j+1, 1]) // 2
            cr_avg = (ycrcb_image[i, j, 2] + ycrcb_image[i, j+1, 2]) // 2
            
            # YUYV format: Y0, Cb, Y1, Cr
            yuv422[i, j*2] = ycrcb_image[i, j, 0]
            yuv422[i, j*2+1] = cb_avg
            yuv422[i, j*2+2] = ycrcb_image[i, j+1, 0]
            yuv422[i, j*2+3] = cr_avg
    
    return yuv422.flatten(), rgb_image


def test_conversion():
    """Test the YUV422 to RGB conversion"""
    print("Generating test color bars in YUV422 (YUYV) format...")
    yuv422_data, original_rgb = generate_color_bar_yuv422()
    
    print(f"YUV422 data size: {len(yuv422_data)} bytes")
    print("Converting YUV422 to RGB...")
    converted_rgb = convert_yuv422_to_rgb(yuv422_data)
    
    # Save original for comparison
    original_img = Image.fromarray(original_rgb)
    original_img.save('/root/projects/img-endpoint/test_original.png')
    print("Saved original reference as: test_original.png")
    
    # Save converted image
    converted_img = Image.fromarray(converted_rgb)
    converted_img.save('/root/projects/img-endpoint/test_converted.png')
    print("Saved converted result as: test_converted.png")
    
    # Convert to JPEG and save
    img_byte_arr = io.BytesIO()
    converted_img.save(img_byte_arr, format='JPEG', quality=85)
    with open('/root/projects/img-endpoint/test_converted.jpg', 'wb') as f:
        f.write(img_byte_arr.getvalue())
    print("Saved JPEG as: test_converted.jpg")
    
    # Compare colors in the middle of each bar
    print("\nColor verification (sampling center of each bar):")
    width, height = 160, 120
    bar_width = width // 8
    
    color_names = ["White", "Yellow", "Cyan", "Green", "Magenta", "Red", "Blue", "Black"]
    expected_colors = [
        (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
        (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)
    ]
    
    for i in range(8):
        bar_center_x = (i * bar_width) + (bar_width // 2)
        sample_y = height // 2
        
        original_pixel = original_rgb[sample_y, bar_center_x]
        converted_pixel = converted_rgb[sample_y, bar_center_x]
        
        diff = abs(original_pixel.astype(int) - converted_pixel.astype(int))
        avg_diff = np.mean(diff)
        
        print(f"  {color_names[i]:8s} | Original: {tuple(original_pixel)} | Converted: {tuple(converted_pixel)} | Avg Diff: {avg_diff:.1f}")
    
    print("\n✅ Test complete! Check the generated images to verify colors are correct.")
    print("   - test_original.png: Reference image")
    print("   - test_converted.png: Converted from YUV422")
    print("   - test_converted.jpg: JPEG version (what Telegram will receive)")


if __name__ == "__main__":
    test_conversion()
