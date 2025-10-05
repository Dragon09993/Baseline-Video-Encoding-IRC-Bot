#!/usr/bin/env python3
"""
IRC Video Bot for x220 encoding
Listens for video URLs in IRC and triggers download/encoding
"""

import asyncio
import os
import re
import logging
from datetime import datetime
from pathlib import Path
import irc.bot
import irc.strings
from irc.client import NickMask
import subprocess
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667, password=None):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, password)], nickname, nickname)
        self.channel = channel
        self.processing_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.process_videos, daemon=True)
        self.worker_thread.start()
        
        # URL patterns for video sites
        self.url_patterns = [
            r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'https?://youtu\.be/[\w-]+',
            r'https?://(?:www\.)?vimeo\.com/\d+',
            r'https?://(?:www\.)?dailymotion\.com/video/[\w-]+',
            r'https?://(?:www\.)?twitch\.tv/videos/\d+',
            # Add more patterns as needed
        ]
        
    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        logger.info(f"Connected to server, joining {self.channel}")
        c.join(self.channel)

    def on_pubmsg(self, c, e):
        """Handle public messages in the channel"""
        message = e.arguments[0]
        nick = e.source.nick
        
        # Look for video URLs in the message
        urls = self.extract_video_urls(message)
        if urls:
            for url in urls:
                logger.info(f"Found video URL from {nick}: {url}")
                c.privmsg(self.channel, f"📹 Processing video: {url}")
                self.processing_queue.put((url, nick))

    def on_privmsg(self, c, e):
        """Handle private messages"""
        message = e.arguments[0]
        nick = e.source.nick
        
        # Look for video URLs in private messages too
        urls = self.extract_video_urls(message)
        if urls:
            for url in urls:
                logger.info(f"Found video URL from {nick} (private): {url}")
                c.privmsg(nick, f"📹 Processing video: {url}")
                self.processing_queue.put((url, nick))

    def extract_video_urls(self, message):
        """Extract video URLs from a message"""
        urls = []
        for pattern in self.url_patterns:
            matches = re.findall(pattern, message)
            urls.extend(matches)
        return urls

    def process_videos(self):
        """Worker thread to process video downloads and encoding"""
        while True:
            try:
                url, requester = self.processing_queue.get()
                logger.info(f"Processing video: {url} requested by {requester}")
                
                success, output_file = self.download_and_encode(url)
                
                if success and output_file:
                    # Notify about completion
                    filename = os.path.basename(output_file)
                    file_url = f"http://10.0.0.2:8084/{filename}"
                    message = f"✅ Video ready: {file_url} (requested by {requester})"
                    self.connection.privmsg(self.channel, message)
                    logger.info(f"Video processing completed: {output_file}")
                else:
                    message = f"❌ Failed to process video: {url} (requested by {requester})"
                    self.connection.privmsg(self.channel, message)
                    logger.error(f"Video processing failed for: {url}")
                    
            except Exception as e:
                logger.error(f"Error in video processing: {e}")
            finally:
                self.processing_queue.task_done()

    def check_nvenc_available(self):
        """Check if NVENC hardware encoding is available"""
        try:
            result = subprocess.run([
                "ffmpeg", "-hide_banner", "-encoders"
            ], capture_output=True, text=True)
            return "h264_nvenc" in result.stdout
        except:
            return False

    def download_and_encode(self, url):
        """Download and encode a video"""
        try:
            # Generate output filename with timestamp
            now = datetime.now()
            timestamp = now.strftime("%m-%d-%y_%H:%M")
            
            # Create temp directory for this download
            temp_dir = Path("/app/temp")
            temp_dir.mkdir(exist_ok=True)
            
            # Download video info first to get title
            logger.info(f"Getting video info for: {url}")
            info_cmd = [
                "yt-dlp", "--get-title", "--get-filename", 
                "-o", "%(title)s.%(ext)s", url
            ]
            
            result = subprocess.run(info_cmd, capture_output=True, text=True, cwd=temp_dir)
            if result.returncode != 0:
                logger.error(f"Failed to get video info: {result.stderr}")
                return False, None
                
            lines = result.stdout.strip().split('\n')
            title = lines[0] if lines else "video"
            
            # Sanitize title for filename
            safe_title = re.sub(r'[^\w\-_\.]', '_', title)[:50]  # Limit length
            
            # Download video
            logger.info(f"Downloading video: {title}")
            download_cmd = [
                "yt-dlp", "-f", "best[height<=720]", 
                "-o", "input_video.%(ext)s", url
            ]
            
            result = subprocess.run(download_cmd, cwd=temp_dir)
            if result.returncode != 0:
                logger.error("Failed to download video")
                return False, None
            
            # Find the downloaded file
            input_files = list(temp_dir.glob("input_video.*"))
            if not input_files:
                logger.error("No input file found after download")
                return False, None
                
            input_file = input_files[0]
            
            # Generate output filename
            output_filename = f"{safe_title}-{timestamp}-x220.mp4"
            output_path = Path("/app/output") / output_filename
            
            # Try GPU encoding first, then fallback to CPU
            success = False
            
            # Check if RTX 4060 NVENC is available
            if self.check_nvenc_available():
                logger.info("RTX 4060 detected! Using GPU encoding (NVENC)...")
                
                # RTX 4060 NVENC encoding - much faster, good quality
                nvenc_cmd = [
                    "ffmpeg", "-i", str(input_file),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                    "-c:v", "h264_nvenc", "-preset", "p4", "-tune", "hq", 
                    "-rc", "vbr", "-cq", "18", "-b:v", "0",
                    "-profile:v", "baseline", "-level", "3.1",
                    "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart",
                    "-y",  # Overwrite output file
                    str(output_path)
                ]
                
                result = subprocess.run(nvenc_cmd)
                if result.returncode == 0:
                    logger.info("NVENC encoding completed successfully")
                    success = True
                else:
                    logger.warning("NVENC encoding failed, falling back to CPU encoding...")
            else:
                logger.info("NVENC not available, using CPU encoding...")
            
            # Fallback to CPU encoding if NVENC failed or not available
            if not success:
                logger.info("Using CPU encoding with x264...")
                cpu_cmd = [
                    "ffmpeg", "-i", str(input_file),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                    "-profile:v", "baseline", "-level", "3.1",
                    "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart",
                    "-y",  # Overwrite output file
                    str(output_path)
                ]
                
                result = subprocess.run(cpu_cmd)
                if result.returncode != 0:
                    logger.error("CPU encoding also failed")
                    return False, None
                    
                success = True
            
            if not success:
                logger.error("All encoding methods failed")
                return False, None
            
            # Clean up temp files
            try:
                input_file.unlink()
                logger.info("Cleaned up temporary files")
            except:
                pass
            
            return True, str(output_path)
            
        except Exception as e:
            logger.error(f"Exception in download_and_encode: {e}")
            return False, None

def main():
    # Get configuration from environment variables
    server = os.getenv('IRC_SERVER', 'irc.libera.chat')
    port = int(os.getenv('IRC_PORT', 6667))
    channel = os.getenv('IRC_CHANNEL', '#test')
    nickname = os.getenv('IRC_NICKNAME', 'videobot')
    password = os.getenv('IRC_PASSWORD')  # Optional
    
    # Ensure output and logs directories exist
    Path("/app/output").mkdir(exist_ok=True)
    Path("/app/logs").mkdir(exist_ok=True)
    
    logger.info(f"Starting IRC Video Bot")
    logger.info(f"Server: {server}:{port}")
    logger.info(f"Channel: {channel}")
    logger.info(f"Nickname: {nickname}")
    
    bot = VideoBot(channel, nickname, server, port, password)
    
    try:
        bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")

if __name__ == "__main__":
    main()