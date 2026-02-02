import requests
import json

# Test script to send an image to the doorbell endpoint

# Server details
SERVER_URL = "https://your-domain.com"  # Replace with your actual domain
ENDPOINT = "/doorbell/"

# Path to a test image file (should be in YUV422 raw format or standard format like JPEG/PNG)
TEST_IMAGE_PATH = "test_image.jpg"  # Replace with your test image path

def test_doorbell_endpoint():
    """
    Test the doorbell endpoint by sending an image
    """
    url = SERVER_URL + ENDPOINT
    
    try:
        with open(TEST_IMAGE_PATH, 'rb') as image_file:
            # Send the image as raw binary data
            headers = {
                'Content-Type': 'application/octet-stream'
            }
            
            response = requests.post(
                url,
                data=image_file.read(),
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("Success! Image was processed and sent to Telegram.")
            else:
                print(f"Error: {response.status_code} - {response.text}")
                
    except FileNotFoundError:
        print(f"Error: Could not find test image at {TEST_IMAGE_PATH}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    test_doorbell_endpoint()