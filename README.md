# IRC Video Bot for x220 Encoding

An automated IRC bot that monitors channels for video URLs, downloads them using yt-dlp, and encodes them with x264 baseline profile optimized for older devices like the ThinkPad x220.

## Features

- 🤖 **IRC Bot**: Monitors IRC channels for video URLs
- 📺 **Video Processing**: Downloads and encodes videos using yt-dlp and ffmpeg
- � **GPU Acceleration**: RTX 4060 NVENC encoding with CPU fallback
- 🎬 **Lighthttpd Server**: Proper video streaming with range requests on port 8084
- 🐋 **Docker**: Fully containerized with Docker Compose and NVIDIA runtime
- 📱 **x220 Optimized**: Encodes with baseline profile for compatibility
- 🌐 **Web Interface**: HTML5 video player with seeking and mobile support

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd IRC-Video-Bot

# Run automated setup (installs NVIDIA Docker if needed)
./setup.sh
```

### 2. Configure IRC Settings

Edit the `.env` file:

```bash
IRC_SERVER=10.0.0.4
IRC_PORT=6667
IRC_CHANNEL=#videos
IRC_NICKNAME=videobot_x220
IRC_PASSWORD=optional_password
```

### 3. Build and Run

```bash
# Build the container with GPU support
docker-compose build

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Access Videos

Once running, access your encoded videos at:
- **Web Interface**: `http://10.0.0.2:8084/` (nginx with HTML5 player)
- **Direct Files**: `http://10.0.0.2:8084/filename.mp4` (streamable videos)
- **Local Access**: `http://localhost:8084/` (from the host machine)

## How It Works

### IRC Bot Operation

1. **Connect**: Bot connects to specified IRC server and joins the configured channel
2. **Monitor**: Listens for messages containing video URLs (YouTube, Vimeo, etc.)
3. **Queue**: Adds detected URLs to a processing queue
4. **Notify**: Announces in channel when processing starts and completes

### Video Processing Pipeline

1. **Download**: Uses yt-dlp to download video in best quality ≤720p
2. **Encode**: Applies ffmpeg encoding with these settings:
   ```bash
   ffmpeg -i input.mov \
     -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p" \
     -c:v libx264 -preset slow -crf 18 -profile:v baseline -level 3.1 \
     -c:a aac -b:a 160k \
     output.mp4
   ```
3. **Save**: Outputs to `/app/output/{videoname}-{MM-dd-yy_HH:MM}-x220.mp4`
4. **Serve**: Makes available via HTTPS server

### File Structure

```
IRC-Video-Bot/
├── src/
│   ├── bot.py              # IRC bot implementation
│   └── file_server.py      # HTTPS file server
├── output/                 # Encoded videos (mounted)
├── temp/                   # Temporary download files
├── logs/                   # Application logs
├── certs/                  # SSL certificates
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
├── .env.example           # Environment configuration template
└── README.md              # This file
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IRC_SERVER` | `irc.libera.chat` | IRC server hostname |
| `IRC_PORT` | `6667` | IRC server port |
| `IRC_CHANNEL` | `#test` | IRC channel to join |
| `IRC_NICKNAME` | `videobot` | Bot's IRC nickname |
| `IRC_PASSWORD` | (empty) | IRC password (optional) |

### Supported Video Sites

The bot automatically detects URLs from:
- YouTube (`youtube.com`, `youtu.be`)
- Vimeo (`vimeo.com`)
- Dailymotion (`dailymotion.com`)
- Twitch (`twitch.tv/videos`)
- Many others supported by yt-dlp

### Encoding Settings Explained

The ffmpeg command is optimized for the ThinkPad x220:

- **Scale filter**: Ensures even dimensions (required for some codecs)
- **yuv420p**: Pixel format for maximum compatibility
- **libx264**: Industry-standard H.264 encoder
- **preset slow**: Better compression at cost of encoding time
- **crf 18**: High quality (18 is near-lossless for most content)
- **baseline profile**: Compatible with older hardware decoders
- **level 3.1**: Supports up to 720p30 or 1080p30
- **AAC audio**: 160k bitrate for good quality

## Usage Examples

### IRC Usage

Just paste video URLs in the monitored channel:

```
<user> Check out this video: https://www.youtube.com/watch?v=dQw4w9WgXcQ
<videobot_x220> 📹 Processing video: https://www.youtube.com/watch?v=dQw4w9WgXcQ
<videobot_x220> ✅ Video ready: http://10.0.0.2:8084/Never_Gonna_Give_You_Up-10-05-25_14:30-x220.mp4 (requested by user)
```

### Web Interface

Navigate to `http://10.0.0.2:8084/` to:
- Browse all encoded videos
- Preview videos with built-in player  
- Download videos directly
- View file information (size, date)

## Management

### Viewing Logs

```bash
# All logs
docker-compose logs -f

# Just IRC bot logs
docker-compose exec irc-video-bot tail -f /app/logs/bot.log

# Check container status
docker-compose ps
```

### Stopping/Starting

```bash
# Stop the bot
docker-compose down

# Start the bot
docker-compose up -d

# Restart the bot
docker-compose restart
```

### Maintenance

```bash
# Clean up old videos (manual)
docker-compose exec irc-video-bot find /app/output -name "*.mp4" -mtime +30 -delete

# Clean up temp files
docker-compose exec irc-video-bot rm -rf /app/temp/*

# Update yt-dlp
docker-compose exec irc-video-bot pip install --upgrade yt-dlp
```

## Troubleshooting

### Bot Not Connecting to IRC

1. Check IRC server settings in `.env`
2. Verify network connectivity: `docker-compose exec irc-video-bot ping irc.libera.chat`
3. Check if nickname is already in use
4. Review logs: `docker-compose logs irc-video-bot`

### Video Downloads Failing

1. Ensure yt-dlp is up to date
2. Check if the video URL is supported
3. Verify internet connectivity in container
4. Check temp directory permissions

### HTTPS Server Issues

1. Certificate generation may fail - falls back to HTTP
2. Check port 8084 is not in use by another service
3. Verify Docker port mapping is correct

### Performance Issues

1. Adjust Docker resource limits in `docker-compose.yml`
2. Consider changing ffmpeg preset from "slow" to "medium" or "fast"
3. Monitor disk space for output directory

## Security Considerations

- The HTTPS server uses self-signed certificates (browser warnings expected)
- Consider using a reverse proxy with proper SSL certificates for production
- The bot downloads and processes arbitrary URLs - monitor resource usage
- IRC connections are typically unencrypted (consider IRC over TLS)

## Development

### Local Development

```bash
# Install dependencies locally
pip install -r requirements.txt

# Run components separately
python src/file_server.py &
python src/bot.py
```

### Customization

- Modify video quality settings in `src/bot.py`
- Adjust ffmpeg parameters for different encoding profiles
- Add support for additional video sites by updating URL patterns
- Customize the web interface in `src/file_server.py`

## License

This project is provided as-is for educational and personal use.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Note**: This bot is designed for personal/educational use. Be respectful of content creators and follow the terms of service for video platforms.