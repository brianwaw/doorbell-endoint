#!/usr/bin/env python3
"""
Test to determine the correct YUV422 format by testing both YUYV and UYVY
"""
import numpy as np
import cv2
from PIL import Image
import io

def yuv_to_rgb(y, u, v):
    """Convert YUV to RGB using standard conversion formulas"""
    y, u, v = float(y), float(u), float(v)
    r = y + 1.402 * (v - 128)
    g = y - 0.344136 * (u - 128) - 0.714136 * (v - 128)
    b = y + 1.772 * (u - 128)
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return r, g, b


def convert_yuyv_to_rgb(yuv422_data, width=160, height=120):
    """Convert YUYV format: Y0, U, Y1, V"""
    yuv422_array = np.frombuffer(yuv422_data, dtype=np.uint8)
    yuv422_reshaped = yuv422_array.reshape((height, width * 2))
    rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    for i in range(height):
        for j in range(0, width * 2, 4):
            if j + 3 < width * 2:
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


def convert_uyvy_to_rgb(yuv422_data, width=160, height=120):
    """Convert UYVY format: U, Y0, V, Y1"""
    yuv422_array = np.frombuffer(yuv422_data, dtype=np.uint8)
    yuv422_reshaped = yuv422_array.reshape((height, width * 2))
    rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    for i in range(height):
        for j in range(0, width * 2, 4):
            if j + 3 < width * 2:
                u = yuv422_reshaped[i, j]
                y0 = yuv422_reshaped[i, j + 1]
                v = yuv422_reshaped[i, j + 2]
                y1 = yuv422_reshaped[i, j + 3]
                
                r0, g0, b0 = yuv_to_rgb(y0, u, v)
                r1, g1, b1 = yuv_to_rgb(y1, u, v)
                
                x0 = j // 2
                x1 = x0 + 1
                if x0 < width:
                    rgb_image[i, x0] = [r0, g0, b0]
                if x1 < width:
                    rgb_image[i, x1] = [r1, g1, b1]
    
    return rgb_image


def generate_test_yuv422(width=160, height=120):
    """Generate YUV422 data with known RGB colors"""
    rgb_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Create color bars
    bar_width = width // 8
    colors = [
        (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
        (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)
    ]
    for i in range(8):
        rgb_image[:, i*bar_width:(i+1)*bar_width] = colors[i]
    
    # Convert to YCrCb
    ycrcb_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2YCrCb)
    
    # Create YUYV format
    yuyv_data = np.zeros((height, width * 2), dtype=np.uint8)
    for i in range(height):
        for j in range(0, width, 2):
            cb_avg = int((ycrcb_image[i, j, 1] + ycrcb_image[i, j+1, 1]) // 2)
            cr_avg = int((ycrcb_image[i, j, 2] + ycrcb_image[i, j+1, 2]) // 2)
            yuyv_data[i, j*2] = ycrcb_image[i, j, 0]      # Y0
            yuyv_data[i, j*2+1] = cb_avg                  # U/Cb
            yuyv_data[i, j*2+2] = ycrcb_image[i, j+1, 0]  # Y1
            yuyv_data[i, j*2+3] = cr_avg                  # V/Cr
    
    return yuyv_data.flatten(), rgb_image


def test_format(yuv_data, converter_func, name):
    """Test a conversion function and report accuracy"""
    rgb_result = converter_func(yuv_data)
    
    width, height = 160, 120
    bar_width = width // 8
    color_names = ["White", "Yellow", "Cyan", "Green", "Magenta", "Red", "Blue", "Black"]
    
    total_error = 0
    print(f"\n{name}:")
    for i in range(8):
        bar_center_x = (i * bar_width) + (bar_width // 2)
        sample_y = height // 2
        converted_pixel = rgb_result[sample_y, bar_center_x]
        
        # Calculate expected color
        colors = [
            (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
            (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)
        ]
        expected = colors[i]
        diff = abs(np.array(expected) - converted_pixel)
        avg_diff = np.mean(diff)
        total_error += avg_diff
        
        status = "✓" if avg_diff < 15 else "✗"
        print(f"  {status} {color_names[i]:8s} | Expected: {expected} | Got: {tuple(converted_pixel)} | Diff: {avg_diff:.1f}")
    
    return total_error / 8


if __name__ == "__main__":
    print("Generating test YUV422 data (YUYV format)...")
    yuv_data, original_rgb = generate_test_yuv422()
    
    print(f"YUV422 data size: {len(yuv_data)} bytes")
    print("=" * 70)
    
    # Test YUYV conversion
    error_yuyv = test_format(yuv_data, convert_yuyv_to_rgb, "YUYV format (Y0,U,Y1,V)")
    
    # Test UYVY conversion
    error_uyvy = test_format(yuv_data, convert_uyvy_to_rgb, "UYVY format (U,Y0,V,Y1)")
    
    print("\n" + "=" * 70)
    print(f"Average error - YUYV: {error_yuyv:.1f}, UYVY: {error_uyvy:.1f}")
    
    if error_yuyv < error_uyvy:
        print("✓ YUYV format produces better results")
    else:
        print("✓ UYVY format produces better results")
