#!/bin/bash

# Test script to send an image to the doorbell endpoint using curl

# Replace with your actual domain
SERVER_URL="https://your-domain.com"  # Change this to your actual domain
ENDPOINT="/doorbell/"
IMAGE_FILE="test_image.jpg"  # Replace with your test image path

echo "Sending image to doorbell endpoint..."

# Send the image as raw binary data
curl -X POST \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@$IMAGE_FILE" \
  "$SERVER_URL$ENDPOINT"

echo ""
echo "Request completed."