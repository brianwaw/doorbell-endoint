#!/usr/bin/env python3
"""
Test using OpenCV's built-in YUV422 conversion
"""
import numpy as np
import cv2
from PIL import Image

def generate_test_yuv422(width=160, height=120):
    """Generate YUV422 data with known RGB colors - format for OpenCV"""
    rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    bar_width = width // 8
    colors = [
        (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
        (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)
    ]
    for i in range(8):
        rgb_image[:, i*bar_width:(i+1)*bar_width] = colors[i]
    
    # Convert to YCrCb
    ycrcb_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2YCrCb)
    
    # Create YUYV format for OpenCV: each pixel has (Y, UV) where UV is shared
    # Shape: (height, width, 2) where [:, :, 0] = Y and [:, :, 1] = interleaved UV
    # For YUYV: pixel 0 has (Y0, U), pixel 1 has (Y1, V), pixel 2 has (Y2, U), etc.
    yuyv_data = np.zeros((height, width, 2), dtype=np.uint8)
    
    for i in range(height):
        for j in range(0, width, 2):
            cb_avg = int((ycrcb_image[i, j, 1] + ycrcb_image[i, j+1, 1]) // 2)
            cr_avg = int((ycrcb_image[i, j, 2] + ycrcb_image[i, j+1, 2]) // 2)
            
            # Pixel j (even): Y0, U
            yuyv_data[i, j, 0] = ycrcb_image[i, j, 0]
            yuyv_data[i, j, 1] = cb_avg
            
            # Pixel j+1 (odd): Y1, V
            yuyv_data[i, j+1, 0] = ycrcb_image[i, j+1, 0]
            yuyv_data[i, j+1, 1] = cr_avg
    
    # Also create raw bytes format (for ESP32 simulation)
    raw_bytes = yuyv_data.reshape((height, width * 2)).flatten()
    
    return raw_bytes, rgb_image, yuyv_data


def test_opencv_yuyv(yuyv_data, width=160, height=120):
    """Use OpenCV to convert YUYV to RGB"""
    # Reshape to (height, width, 2) - 2 channels for YUV422
    yuyv_reshaped = yuyv_data.reshape((height, width, 2))
    
    # OpenCV expects YUV422 in a specific format
    # Try COLOR_YUV2BGR_YUYV
    rgb_image = cv2.cvtColor(yuyv_reshaped, cv2.COLOR_YUV2BGR_YUYV)
    return rgb_image


def test_opencv_uyvy(yuyv_data, width=160, height=120):
    """Use OpenCV to convert UYVY to RGB"""
    yuyv_reshaped = yuyv_data.reshape((height, width, 2))
    rgb_image = cv2.cvtColor(yuyv_reshaped, cv2.COLOR_YUV2BGR_UYVY)
    return rgb_image


def evaluate_result(rgb_result, original_rgb, name):
    """Evaluate conversion accuracy"""
    width, height = 160, 120
    bar_width = width // 8
    color_names = ["White", "Yellow", "Cyan", "Green", "Magenta", "Red", "Blue", "Black"]
    
    total_error = 0
    print(f"\n{name}:")
    for i in range(8):
        bar_center_x = (i * bar_width) + (bar_width // 2)
        sample_y = height // 2
        
        # OpenCV returns BGR, convert to RGB for comparison
        if rgb_result.shape[2] == 3:
            converted_pixel = rgb_result[sample_y, bar_center_x]
            # If BGR, convert to RGB for display
            converted_display = (converted_pixel[2], converted_pixel[1], converted_pixel[0])
        else:
            converted_display = (0, 0, 0)
        
        colors = [
            (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
            (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)
        ]
        expected = colors[i]
        diff = abs(np.array(expected) - np.array(converted_display))
        avg_diff = np.mean(diff)
        total_error += avg_diff
        
        status = "✓" if avg_diff < 15 else "✗"
        print(f"  {status} {color_names[i]:8s} | Expected: {expected} | Got: {converted_display} | Diff: {avg_diff:.1f}")
    
    return total_error / 8


if __name__ == "__main__":
    print("Generating test YUV422 data...")
    yuyv_data, original_rgb = generate_test_yuv422()
    
    # Save original for reference
    Image.fromarray(original_rgb).save('/root/projects/img-endpoint/test_original.png')
    
    print(f"YUV422 data size: {yuyv_data.size} bytes")
    print("=" * 70)
    
    # Test with OpenCV YUYV conversion
    try:
        result_yuyv = test_opencv_yuyv(yuyv_data)
        error_yuyv = evaluate_result(result_yuyv, original_rgb, "OpenCV COLOR_YUV2BGR_YUYV")
        Image.fromarray(cv2.cvtColor(result_yuyv, cv2.COLOR_BGR2RGB)).save('/root/projects/img-endpoint/test_opencv_yuyv.png')
    except Exception as e:
        print(f"YUYV conversion failed: {e}")
        error_yuyv = float('inf')
    
    # Test with OpenCV UYVY conversion
    try:
        result_uyvy = test_opencv_uyvy(yuyv_data)
        error_uyvy = evaluate_result(result_uyvy, original_rgb, "OpenCV COLOR_YUV2BGR_UYVY")
        Image.fromarray(cv2.cvtColor(result_uyvy, cv2.COLOR_BGR2RGB)).save('/root/projects/img-endpoint/test_opencv_uyvy.png')
    except Exception as e:
        print(f"UYVY conversion failed: {e}")
        error_uyvy = float('inf')
    
    print("\n" + "=" * 70)
    print(f"Average error - YUYV: {error_yuyv:.1f}, UYVY: {error_uyvy:.1f}")
    
    if error_yuyv < error_uyvy:
        print("✓ YUYV format produces better results")
    else:
        print("✓ UYVY format produces better results")
    
    print("\nCheck generated images:")
    print("  - test_original.png: Reference")
    print("  - test_opencv_yuyv.png: YUYV conversion")
    print("  - test_opencv_uyvy.png: UYVY conversion")
