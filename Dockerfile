# Use Ubuntu base image - NVIDIA runtime will be added via docker-compose
FROM ubuntu:22.04

# Install system dependencies including nginx for video serving
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    nginx \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Install yt-dlp
RUN pip install --no-cache-dir yt-dlp

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create application directories
RUN mkdir -p /app/src /app/output /app/temp /app/logs /app/www \
    /var/log/lighthttpd /var/cache/lighthttpd/compress /var/cache/lighthttpd/uploads

# Set working directory
WORKDIR /app

# Copy application files
COPY src/ ./src/
COPY nginx.conf /etc/nginx/sites-available/videobot
COPY www/ ./www/

# Set up nginx configuration and permissions
RUN mkdir -p /var/log/nginx && \
    rm -f /etc/nginx/sites-enabled/default && \
    ln -sf /etc/nginx/sites-available/videobot /etc/nginx/sites-enabled/ && \
    chown -R www-data:www-data /app/output /app/www /var/log/nginx && \
    nginx -t

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting IRC Video Bot for x220 with GPU support..."\n\
\n\
# Check for GPU\n\
if command -v nvidia-smi >/dev/null 2>&1; then\n\
    echo "NVIDIA GPU detected:"\n\
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null || echo "GPU info unavailable"\n\
else\n\
    echo "No NVIDIA GPU detected, will use CPU encoding"\n\
fi\n\
\n\
# Ensure output directory exists and has correct permissions\n\
mkdir -p /app/output\n\
chown www-data:www-data /app/output\n\
\n\
# Start nginx web server\n\
echo "Starting nginx server on port 8084..."\n\
nginx -g "daemon off;" &\n\
NGINX_PID=$!\n\
\n\
# Wait a moment for server to start\n\
sleep 3\n\
\n\
# Start IRC bot\n\
echo "Starting IRC bot..."\n\
python src/bot.py &\n\
BOT_PID=$!\n\
\n\
# Function to handle shutdown\n\
shutdown() {\n\
    echo "Shutting down..."\n\
    kill $NGINX_PID 2>/dev/null || true\n\
    kill $BOT_PID 2>/dev/null || true\n\
    exit 0\n\
}\n\
\n\
# Set up signal handlers\n\
trap shutdown SIGINT SIGTERM\n\
\n\
# Wait for processes\n\
wait $BOT_PID\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Set up permissions
RUN chmod -R 755 /app/src
RUN chmod 777 /app/temp /app/logs

# Expose ports
EXPOSE 8084

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8084/ || exit 1

# Run the application
ENTRYPOINT ["/app/entrypoint.sh"]