# ESP32-CAM to Telegram Doorbell Service

This service receives images from an ESP32-CAM, processes them to JPEG format, and sends them to a Telegram bot with a notification message.

## Architecture

- **ESP32-CAM**: Captures images in YUV422 format at QQVGA resolution (160x120)
- **FastAPI Endpoint**: Receives images, processes them to JPEG, and forwards to Telegram
- **Telegram Bot**: Receives images and notifications
- **Nginx**: Routes `/doorbell/` requests to the FastAPI service

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in the `/root/projects/img-endpoint/` directory:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 2. Deploy the Service

From the `/root/projects/img-endpoint/` directory:

```bash
# Build and start the service
docker-compose up -d

# The service will be available internally at:
# http://img-endpoint:8000
```

### 3. ESP32-CAM Code

Configure your ESP32-CAM to send images to your server's `/doorbell/` endpoint:

```cpp
// Example Arduino code snippet
HTTPClient http;
http.begin("http://your-server-ip/doorbell/");
http.addHeader("Content-Type", "application/octet-stream");

int httpResponseCode = http.POST(imageData, imageSize);
```

### 4. Testing

After deployment, you can test the endpoint:

```bash
curl -X POST "http://your-domain/doorbell/" -H "Content-Type: application/octet-stream" --data-binary @test_image.jpg
```

## Endpoints

- `POST /doorbell/` - Main endpoint for ESP32-CAM images
- `POST /img-api/` - Alternative endpoint for image processing
- `GET /` - Health check endpoint

## How It Works

1. ESP32-CAM captures an image in YUV422 format (QQVGA resolution)
2. Image is sent via HTTP POST to `/doorbell/` endpoint
3. Service validates image format and converts YUV422 to RGB to JPEG
4. JPEG image and notification message are sent to Telegram bot
5. User receives notification with image in Telegram

## Troubleshooting

- Check logs: `docker-compose logs img-endpoint-service`
- Verify environment variables are set correctly
- Ensure nginx configuration is properly routing requests
- Confirm Telegram bot token and chat ID are valid