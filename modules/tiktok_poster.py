"""
TikTok video posting via tiktok-uploader.
Authenticates using TIKTOK_COOKIES (JSON array of browser cookies).
"""

import json
import logging
import os
import tempfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class TikTokPoster:
    def __init__(self):
        self.cookies_json = os.environ.get("TIKTOK_COOKIES", "").strip()
        if not self.cookies_json:
            raise ValueError("TIKTOK_COOKIES must be set in environment")

    def post(self, video_url: str, caption: str) -> dict:
        from tiktok_uploader.upload import upload_video
        from tiktok_uploader.auth import AuthBackend

        tmp_video = Path(tempfile.mktemp(suffix=".mp4"))
        tmp_cookies = Path(tempfile.mktemp(suffix=".json"))
        try:
            self._download(video_url, tmp_video)

            cookies = json.loads(self.cookies_json)
            tmp_cookies.write_text(json.dumps(cookies), encoding="utf-8")

            logger.info(f"Posting to TikTok: {caption[:80]}")
            auth = AuthBackend(cookies=str(tmp_cookies))
            failed = upload_video(
                str(tmp_video),
                description=caption,
                auth=auth,
            )

            if failed:
                raise RuntimeError(f"TikTok upload failed: {failed}")

            logger.info("Posted to TikTok successfully")
            return {"status": "success"}

        finally:
            if tmp_video.exists():
                tmp_video.unlink()
            if tmp_cookies.exists():
                tmp_cookies.unlink()

    def _download(self, url: str, dest: Path) -> None:
        logger.info(f"Downloading video from R2: {url[:80]}")
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        size_mb = round(dest.stat().st_size / 1024 / 1024, 1)
        logger.info(f"Downloaded {size_mb} MB -> {dest.name}")
