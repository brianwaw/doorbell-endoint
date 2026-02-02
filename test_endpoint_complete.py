#!/usr/bin/env python3

import requests
import sys
import os

def test_doorbell_endpoint(server_url, image_path=None):
    """
    Test the doorbell endpoint by sending an image
    :param server_url: Full URL to your server (e.g., https://yourdomain.com)
    :param image_path: Path to the image file to send (optional, will create test data if None)
    """
    
    endpoint = server_url.rstrip('/') + '/doorbell/'
    
    # If no image path provided, create test data that mimics ESP32-CAM YUV422 format
    if image_path is None:
        # Create test data that matches QQVGA YUV422 format (160x120, 2 bytes per pixel = 38400 bytes)
        # This simulates the raw YUV422 data from ESP32-CAM
        test_data = bytearray([i % 256 for i in range(38400)])  # QQVGA YUV422 size
        data_to_send = test_data
        print("Using generated test data (QQVGA YUV422 format)")
    else:
        if not os.path.exists(image_path):
            print(f"Error: Image file not found: {image_path}")
            return False
        with open(image_path, 'rb') as f:
            data_to_send = f.read()
        print(f"Using image file: {image_path}")
    
    try:
        print(f"Sending request to: {endpoint}")
        
        # Send the image as raw binary data (application/octet-stream)
        headers = {
            'Content-Type': 'application/octet-stream'
        }
        
        response = requests.post(
            endpoint,
            data=data_to_send,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Success! Image was processed and sent to Telegram.")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Could not connect to the server. Check the URL and network connectivity.")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: Request timed out. The server might be busy processing the image.")
        return False
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_endpoint.py <server_url> [image_path]")
        print("Example: python3 test_endpoint.py https://yourdomain.com")
        print("Example: python3 test_endpoint.py https://yourdomain.com /path/to/image.jpg")
        sys.exit(1)
    
    server_url = sys.argv[1]
    image_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = test_doorbell_endpoint(server_url, image_path)
    
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")
        sys.exit(1)