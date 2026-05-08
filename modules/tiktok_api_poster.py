"""
TikTok Content Posting API (official).
https://developers.tiktok.com/products/content-posting-api/

Requires env vars:
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN, TIKTOK_REFRESH_TOKEN
"""

import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")


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
        """Post video to TikTok via pull-from-URL method."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        body = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "SELF_ONLY",  # until app audit passes
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
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
            headers["Authorization"] = f"Bearer {self.access_token}"
            resp = requests.post(
                f"{self.BASE_URL}/post/publish/video/init/",
                json=body,
                headers=headers,
            )

        data = resp.json()
        logger.info("TikTok init response: %s", data)

        if data.get("error", {}).get("code") not in ("ok", None, ""):
            raise RuntimeError(f"TikTok API error: {data}")

        publish_id = data.get("data", {}).get("publish_id")
        if not publish_id:
            raise RuntimeError(f"No publish_id in response: {data}")

        return self._poll_status(publish_id, headers)

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
