import requests  # For fetching proxy IPs dynamically
from yt_dlp import YoutubeDL
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from telegram import Update
import subprocess
import shlex
import os
from dotenv import load_dotenv
import re
import sys

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Maximum file size for Telegram (in bytes)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_SEGMENT_SIZE = 2 * 1000 * 1000 * 1024  # 1900MB

UPLOAD_TIMEOUT = 20 * 60 * 60  # 20 hours

cookies_file = "cookies.txt"

# Directory to save downloaded files
DOWNLOAD_DIR = "downloads"

stream_url = None
output_filename = None
final_output_path = None

# Ensure the download directory exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


def get_new_proxy():
    """
    Fetch a new proxy address dynamically from a proxy API or free proxy list.
    Replace this function with your preferred proxy source.
    """
    try:
        # Fetching from a free proxy list (example: https://free-proxy-list.net)
        response = requests.get('https://api.getproxylist.com/proxy')
        if response.status_code == 200:
            proxy_data = response.json()
            proxy_ip = proxy_data['ip']
            proxy_port = proxy_data['port']
            return f"http://{proxy_ip}:{proxy_port}"
        else:
            print("Failed to fetch proxy, using default proxy...")
    except Exception as e:
        print(f"Error fetching proxy: {e}")
    return None


async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Hi! Use the following commands to download a video:\n"
        "/seturl <stream_url> - Set the stream URL.\n"
        "/setfilename <file_name> - Set the file name (with or without spaces).\n"
        "/download - Start downloading the video."
    )


async def set_url(update: Update, context: CallbackContext) -> None:
    """Set the URL for the video."""
    global stream_url
    if context.args:
        stream_url = context.args[0]
        await update.message.reply_text(f"Stream URL set to: {stream_url}")
    else:
        await update.message.reply_text("Please provide a stream URL. Example: /seturl http://example.com/stream")


async def set_filename(update: Update, context: CallbackContext) -> None:
    """Set the output filename."""
    global output_filename
    if context.args:
        output_filename = " ".join(context.args) + ".mp4"
        await update.message.reply_text(f"Output filename set to: {output_filename}")
    else:
        await update.message.reply_text("Please provide a filename. Example: /setfilename my_video")


async def download(update: Update, context: CallbackContext) -> None:
    """Download the stream using yt-dlp and convert it to MP4 with FFmpeg."""
    global stream_url, output_filename, final_output_path

    if not stream_url or not output_filename:
        await update.message.reply_text("Please set the stream URL and filename first using /seturl and /setfilename.")
        return

    await update.message.reply_text(f"Starting download of the stream from: {stream_url}")

    temp_output_path = os.path.join(DOWNLOAD_DIR, "temp_video")  # Temporary file
    final_output_path = os.path.join(DOWNLOAD_DIR, output_filename)  # Final MP4 file

    # Get a new proxy for this download
    proxy = get_new_proxy()
    if proxy:
        print(f"Using proxy: {proxy}")
    else:
        print("No proxy available; proceeding without proxy.")

    ydl_opts = {
        'outtmpl': temp_output_path,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        # 'cookiesfrombrowser': ('chrome',),  # Use cookies from Chrome browser
        'cookiefile': cookies_file,
        'verbose': True,
        'quiet': False,
        'proxy': proxy,  # Use the fetched proxy
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.41 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
            'Referer': 'https://www.jiocinema.com/sports/cricket/india-vs-new-zealand-1st-test-day-3-replay/4040532',
            'Origin': 'https://www.jiocinema.com'
        },
        'geo_bypass': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.cache.remove()
            ydl.download([stream_url])

        # Convert the file to MP4 using FFmpeg
        command = [
            "ffmpeg",
            "-i", temp_output_path,
            "-c", "copy",
            "-f", "mp4",
            final_output_path
        ]
        subprocess.run(command, check=True)

        await update.message.reply_text(f"Download and conversion completed. Saved as: {final_output_path}")

        # Clean up temporary files
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        
        # Read the file
        with open(".env", "r") as file:
            lines = file.readlines()

        updated = False
        with open(".env", "w") as file:
            for line in lines:
                if re.match(f"^VIDEO_FILE_PATH=", line):
                    file.write(f"VIDEO_FILE_PATH={final_output_path}\n")
                    updated = True
                else:
                    file.write(line)
            if not updated:
                file.write(f"VIDEO_FILE_PATH={final_output_path}\n")
            

    except Exception as e:
        await update.message.reply_text(f"Error during download or conversion: {e}")
    finally:
        sys.exit()


def main():
    """Start the bot."""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("seturl", set_url))
    application.add_handler(CommandHandler("setfilename", set_filename))
    application.add_handler(CommandHandler("download", download))

    print("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
