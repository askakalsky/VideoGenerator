"""
Test posting a local video file to TikTok.
Usage: python test_post_video.py <video_path> [caption]
"""
import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from dotenv import load_dotenv
load_dotenv()

from modules.tiktok_poster import TikTokPoster

video_path = sys.argv[1] if len(sys.argv) > 1 else r"D:\Downloads\Part_2.mp4"
caption = sys.argv[2] if len(sys.argv) > 2 else "Test post"

print(f"Video: {video_path}")
print(f"Caption: {caption}")

poster = TikTokPoster()
poster.post_local(video_path, caption)
