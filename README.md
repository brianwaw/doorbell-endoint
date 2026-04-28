# ESP32-CAM to Telegram Doorbell Service

This service receives images from an ESP32-CAM, processes them to JPEG format, uses Ollama AI to filter out meaningless images, and sends only relevant images (e.g., those containing people) to a Telegram bot with a notification message.

## Architecture

- **ESP32-CAM**: Captures images in YUV422 format at QQVGA resolution (160x120)
- **FastAPI Endpoint**: Receives images, processes them to JPEG, filters via Ollama, and forwards to Telegram
- **Ollama**: AI model (`qwen3.5:cloud`) that analyzes images to determine if they contain anything worth notifying about
- **Telegram Bot**: Receives filtered images and notifications
- **Nginx**: Routes `/doorbell/` requests to the FastAPI service

## Setup Instructions

### 1. Install Ollama

Ensure Ollama is installed and running on your system:

```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the qwen3.5:cloud model
ollama pull qwen3.5:cloud

# Start Ollama (if not running as a service)
ollama serve
```

Verify Ollama is accessible:
```bash
curl http://localhost:11434
```

### 2. Environment Variables

Create a `.env` file in the project directory:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. Deploy the Service

From the project directory:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or if using Docker
docker-compose up -d
```

### 4. ESP32-CAM Code

Configure your ESP32-CAM to send images to your server's `/doorbell/` endpoint:

```cpp
// Example Arduino code snippet
HTTPClient http;
http.begin("http://your-server-ip/doorbell/");
http.addHeader("Content-Type", "application/octet-stream");

int httpResponseCode = http.POST(imageData, imageSize);
```

### 5. Testing

After deployment, you can test the endpoint:

```bash
curl -X POST "http://your-domain/doorbell/" -H "Content-Type: application/octet-stream" --data-binary @test_image.jpg
```

## Endpoints

- `POST /doorbell/` - Main endpoint for ESP32-CAM images (with Ollama filtering)
- `POST /doorbell/upload/` - Alternative endpoint for file upload format (with Ollama filtering)
- `POST /doorbell_simple/` - Simple endpoint for pre-formatted images (with Ollama filtering)
- `GET /` - Health check endpoint

## How It Works

1. ESP32-CAM captures an image in YUV422 format (QQVGA resolution)
2. Image is sent via HTTP POST to `/doorbell/` endpoint
3. Service validates image format and converts YUV422 to RGB to JPEG
4. **Ollama AI analyzes the JPEG to determine if it contains anything worth notifying about**
5. If Ollama determines the image is worth sending (contains a person or important content), it is forwarded to Telegram
6. If Ollama filters out the image (empty scene, meaningless objects), a `{"status": "filtered"}` response is returned
7. User receives filtered notifications with relevant images in Telegram

## Ollama Filtering

The service uses Ollama's `qwen3.5:cloud` model to analyze images with the following logic:

- **Allowed images**: Images containing people, or anything important that warrants a doorbell notification
- **Filtered images**: Empty scenes, walls, furniture, or uninteresting objects

The model responds with "YES" (send) or "NO" (filter). If Ollama is unavailable, the service defaults to allowing images through (fail-safe behavior).

## Troubleshooting

- Check logs: `docker-compose logs img-endpoint-service` or `journalctl -u ollama`
- Verify Ollama is running: `curl http://localhost:11434`
- Ensure the `qwen3.5:cloud` model is pulled: `ollama list`
- Verify environment variables are set correctly
- Ensure nginx configuration is properly routing requests
- Confirm Telegram bot token and chat ID are valid
