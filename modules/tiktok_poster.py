"""
TikTok video posting via Playwright browser automation (tiktok-uploader).
Authenticates using TIKTOK_SESSION_ID cookie (sessionid from browser).
"""

import logging
import os
import tempfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class TikTokPoster:
    def __init__(self):
        self.session_id = os.environ.get("TIKTOK_SESSION_ID", "").strip()
        if not self.session_id:
            raise ValueError("TIKTOK_SESSION_ID must be set in environment")

    def post(self, video_url: str, caption: str) -> dict:
        """Download video from R2 URL and post to TikTok."""
        from tiktok_uploader.upload import upload_video
        from tiktok_uploader.auth import AuthBackend

        tmp_path = Path(tempfile.mktemp(suffix=".mp4"))
        try:
            self._download(video_url, tmp_path)

            logger.info(f"Posting to TikTok: {caption[:80]}")
            auth = AuthBackend(cookies_list=[{"name": "sessionid", "value": self.session_id}])
            failed = upload_video(
                str(tmp_path),
                description=caption,
                auth=auth,
            )

            if failed:
                raise RuntimeError(f"TikTok upload failed: {failed}")

            logger.info("Posted to TikTok successfully")
            return {"status": "success"}

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def _download(self, url: str, dest: Path) -> None:
        logger.info(f"Downloading video from R2: {url[:80]}")
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        size_mb = round(dest.stat().st_size / 1024 / 1024, 1)
        logger.info(f"Downloaded {size_mb} MB -> {dest.name}")
