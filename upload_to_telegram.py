import os
import math
from telethon import TelegramClient, sync
from telethon.tl.types import DocumentAttributeVideo
from tqdm import tqdm  # For progress bar
from moviepy.editor import VideoFileClip
import subprocess
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Define constants
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_PHONE_NUMBER = os.getenv('TELEGRAM_PHONE_NUMBER')  # Your Telegram phone number
VIDEO_FILE_PATH = os.getenv('VIDEO_FILE_PATH')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))


def get_video_metadata(file_path):
    """
    Retrieves the metadata (duration, width, height) of a video file using ffmpeg.
    
    :param file_path: Path to the video file.
    :return: A tuple (duration, width, height).
    """
    try:
        # Use ffprobe to get metadata
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        metadata = result.stdout.strip().split("\n")
        duration = int(float(metadata[0]))  # First value: duration
        width = int(metadata[1])       # Second value: width
        height = int(metadata[2])      # Third value: height
        return duration, width, height
    except Exception as e:
        print(f"Error getting video metadata: {e}")
        return 0, 0, 0


def split_file(file_path, chunk_size):
    """
    Splits the given file into chunks of specified size.
    """
    chunk_files = []
    chunk_duration = 120 * 60

    output_dir = f"{file_path}_chunks"
    os.makedirs(output_dir, exist_ok=True)

    output_pattern = os.path.join(output_dir, "chunk_%03d.mp4")

    command = [
        "ffmpeg",
        "-i", file_path,
        "-c", "copy",  # Copy codec to avoid re-encoding
        "-map", "0",
        "-segment_time", str(chunk_duration),
        "-f", "segment",
        "-reset_timestamps", "1",
        output_pattern
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Video successfully split into chunks in {output_dir}.")
    except subprocess.CalledProcessError as e:
        print(f"Error while splitting video: {e}")
        return []

    # Collect all chunk file paths
    chunk_files = [os.path.join(output_dir, f) for f in sorted(
        os.listdir(output_dir)) if f.endswith(".mp4")]
    return chunk_files


def upload_video(client, chat_id, file_path):
    file_size = os.path.getsize(file_path)
    progress_bar = tqdm(total=file_size, unit='B',
                        unit_scale=True, desc=os.path.basename(file_path))

    def progress_callback(current, total):
        progress_bar.n = current
        progress_bar.last_print_n = current  # Ensures progress bar updates correctly
        progress_bar.refresh()

    try:
        duration, width, height = get_video_metadata(file_path)
        client.send_file(
            TELEGRAM_CHAT_ID,
            file_path,
            video_note=False,  # Ensures the file is sent as a video
            attributes=[
                DocumentAttributeVideo(
                    duration=int(duration),
                    w=width,
                    h=height,
                    supports_streaming=True  # Enable streaming playback
                )
            ],
            caption=f"Uploading chunk: {os.path.basename(file_path)}",
            progress_callback=progress_callback
        )
        print(f"Uploaded {file_path} successfully.")
    except Exception as e:
        print(f"Failed to upload {file_path}: {e}")
        return False
    return True

def delete_chunk_file(file_path):
    """Deletes a chunk file after it has been uploaded."""
    try:
        os.remove(file_path)
        print(f"Deleted chunk: {file_path}")
    except Exception as e:
        print(f"Failed to delete chunk {file_path}: {e}")


if __name__ == "__main__":
    # # Input values
    # video_file_path = input("Enter the path to the video file: ").strip()
    # chat_id = input("Enter the chat ID or username: ").strip()
    
    # Telethon client setup
    client = TelegramClient("session_name", TELEGRAM_API_ID, TELEGRAM_API_HASH)

    # Login using the phone number
    client.start(phone=TELEGRAM_PHONE_NUMBER)

    # Maximum chunk size: 2GB (Telegram's limit)
    chunk_size = 2 * 1000 * 1000 * 1024

    # Split the file into chunks
    print("Splitting the video file into 2GB chunks...")
    chunks = split_file(VIDEO_FILE_PATH, chunk_size)

    # Upload each chunk to Telegram
    print("Uploading chunks to Telegram...")
    for chunk in chunks:
        if upload_video(client, TELEGRAM_CHAT_ID, chunk):
            delete_chunk_file(chunk)  # Delete the chunk after successful upload

    print("All chunks have been uploaded.")
    client.disconnect()
