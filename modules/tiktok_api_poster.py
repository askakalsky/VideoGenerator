"""
TikTok Content Posting API (official) — push_by_file method.
Downloads video from R2 URL, uploads directly to TikTok in chunks.

Requires env vars:
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN, TIKTOK_REFRESH_TOKEN
"""

import logging
import math
import os
import re
import tempfile
import time

import requests

logger = logging.getLogger(__name__)

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
MIN_CHUNK_SIZE = 5 * 1024 * 1024   # 5 MB (TikTok minimum)
MAX_CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB (TikTok maximum)


class TikTokAPIPoster:
    BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(self):
        self.client_key = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
        self.client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
        self.access_token = os.environ.get("TIKTOK_ACCESS_TOKEN", "").strip()
        self.refresh_token = os.environ.get("TIKTOK_REFRESH_TOKEN", "").strip()

        if not self.access_token:
            raise ValueError("TIKTOK_ACCESS_TOKEN not set. Run get_tiktok_oauth_token.py.")

    def post(self, video_url: str, caption: str) -> dict:
        """Download video from URL, upload to TikTok via push_by_file."""
        logger.info("Downloading video from R2...")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
            resp = requests.get(video_url, stream=True, timeout=120)
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)

        try:
            return self._upload_file(tmp_path, caption)
        finally:
            os.unlink(tmp_path)

    def _upload_file(self, video_path: str, caption: str) -> dict:
        file_size = os.path.getsize(video_path)
        # Use single chunk if file fits in max chunk size, else split into ~10MB chunks
        if file_size <= MAX_CHUNK_SIZE:
            chunk_size = file_size
            chunk_count = 1
        else:
            chunk_size = max(MIN_CHUNK_SIZE, min(MAX_CHUNK_SIZE, 10 * 1024 * 1024))
            chunk_count = math.ceil(file_size / chunk_size)

        headers = self._auth_headers()

        body = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "SELF_ONLY",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": chunk_count,
            },
        }

        resp = requests.post(
            f"{self.BASE_URL}/post/publish/video/init/",
            json=body,
            headers=headers,
        )

        if resp.status_code == 401:
            logger.info("Access token expired, refreshing...")
            self.access_token = self._refresh_access_token()
            headers = self._auth_headers()
            resp = requests.post(
                f"{self.BASE_URL}/post/publish/video/init/",
                json=body,
                headers=headers,
            )

        data = resp.json()
        logger.info("TikTok init response: %s", data)

        err_code = data.get("error", {}).get("code", "ok")
        if err_code not in ("ok", None, ""):
            raise RuntimeError(f"TikTok API error: {data}")

        upload_url = data["data"]["upload_url"]
        publish_id = data["data"]["publish_id"]

        self._upload_chunks(video_path, upload_url, file_size, chunk_size, chunk_count)
        return self._poll_status(publish_id, headers)

    def _upload_chunks(self, video_path: str, upload_url: str, file_size: int, chunk_size: int, chunk_count: int):
        with open(video_path, "rb") as f:
            for i in range(chunk_count):
                chunk = f.read(chunk_size)
                start = i * chunk_size
                end = min(start + len(chunk) - 1, file_size - 1)
                headers = {
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Type": "video/mp4",
                }
                resp = requests.put(upload_url, data=chunk, headers=headers, timeout=120)
                resp.raise_for_status()
                logger.info("Uploaded chunk %d/%d", i + 1, chunk_count)

    def _poll_status(self, publish_id: str, headers: dict) -> dict:
        for _ in range(30):
            time.sleep(10)
            resp = requests.post(
                f"{self.BASE_URL}/post/publish/status/fetch/",
                json={"publish_id": publish_id},
                headers=headers,
            )
            data = resp.json()
            status = data.get("data", {}).get("status", "")
            logger.info("TikTok publish status: %s", status)
            if status == "PUBLISH_COMPLETE":
                logger.info("Video published successfully!")
                return data
            if status in ("FAILED", "PUBLISH_FAILED"):
                raise RuntimeError(f"TikTok publish failed: {data}")
        raise RuntimeError("TikTok publish timed out after 5 minutes")

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def _refresh_access_token(self) -> str:
        resp = requests.post(
            f"{self.BASE_URL}/oauth/token/",
            data={
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = resp.json()
        new_token = data.get("access_token")
        if not new_token:
            raise RuntimeError(f"Failed to refresh token: {data}")

        self.access_token = new_token
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        _update_env("TIKTOK_ACCESS_TOKEN", new_token)
        _update_env("TIKTOK_REFRESH_TOKEN", self.refresh_token)
        return new_token


def _update_env(key: str, value: str):
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(rf"^{key}=.*$", f"{key}={value}", content, flags=re.MULTILINE)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(content)
