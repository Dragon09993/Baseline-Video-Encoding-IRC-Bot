#!/bin/bash

# Setup script for IRC Video Bot with GPU support
set -e

echo "🤖 IRC Video Bot Setup with RTX 4060 Support"
echo "============================================="

# Check if running as root for Docker setup
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root"
    echo "💡 Run as your regular user, we'll prompt for sudo when needed"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker is not installed"
    echo "💡 Please install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose >/dev/null 2>&1; then
    echo "❌ Docker Compose is not installed"
    echo "💡 Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose
fi

# Check for NVIDIA GPU
if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "⚠️  NVIDIA drivers not found"
    echo "💡 The bot will work but will use CPU encoding only"
    echo "💡 For GPU acceleration, install NVIDIA drivers first"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits
fi

# Check for NVIDIA Docker runtime
if ! docker info 2>/dev/null | grep -q nvidia; then
    echo "⚠️  NVIDIA Docker runtime not found"
    echo "💡 Installing NVIDIA Container Toolkit for GPU support..."
    
    # Install NVIDIA Container Toolkit
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
    
    sudo apt-get update
    sudo apt-get install -y nvidia-docker2
    
    echo "🔄 Restarting Docker to enable NVIDIA runtime..."
    sudo systemctl restart docker
    
    echo "✅ NVIDIA Docker runtime installed"
else
    echo "✅ NVIDIA Docker runtime is available"
fi

# Check if user is in docker group
if ! groups | grep -q docker; then
    echo "⚠️  User not in docker group"
    echo "💡 Adding user to docker group..."
    sudo usermod -aG docker $USER
    echo "⚠️  You'll need to log out and back in for group changes to take effect"
    echo "💡 Or run: newgrp docker"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "💡 Please edit .env file to configure your IRC settings"
    echo "💡 Required settings:"
    echo "   - IRC_SERVER (your IRC server)"
    echo "   - IRC_CHANNEL (your channel, e.g., #yourchannel)"
    echo "   - IRC_NICKNAME (your bot's nickname)"
else
    echo "✅ .env file already exists"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p output temp logs www certs

# Set permissions
chmod 755 output temp logs www

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your IRC settings"
echo "2. Build and start: docker-compose up -d"
echo "3. View logs: docker-compose logs -f"
echo "4. Access web interface: http://localhost:8084"
echo ""
echo "GPU Features:"
echo "- RTX 4060 NVENC encoding (much faster)"
echo "- Automatic fallback to CPU if GPU unavailable"
echo "- Hardware-accelerated video processing"
echo ""
echo "Web Features:"
echo "- Lighthttpd server for proper video streaming"
echo "- HTML5 video player with seeking support"
echo "- Range request support for efficient streaming"
echo "- Mobile-responsive interface"