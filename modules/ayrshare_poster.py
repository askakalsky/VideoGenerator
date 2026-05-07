"""
Ayrshare social media posting integration.
Posts video URLs to TikTok (and optionally other platforms).
"""

import logging
import os
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_AYRSHARE_API_URL = "https://app.ayrshare.com/api/post"


class AyrsharePosting:
    """Post videos to social media via Ayrshare API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("AYRSHARE_API_KEY")
        if not self.api_key:
            raise ValueError("AYRSHARE_API_KEY не найден в переменных окружения.")

    def post(
        self,
        video_url: str,
        caption: str,
        platforms: Optional[List[str]] = None,
    ) -> Dict:
        """
        Post a video to social platforms.

        Args:
            video_url: Public URL of the video (from Cloudflare R2).
            caption: Post caption / description.
            platforms: List of platform names (default: ["tiktok"]).

        Returns:
            Ayrshare response dict with keys: status, id, postUrl.
        """
        if platforms is None:
            platforms = ["tiktok"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "post": caption,
            "platforms": platforms,
            "mediaUrls": [video_url],
        }

        logger.info(f"📲 Ayrshare: публикация в {platforms}")
        logger.info(f"   ├─ URL: {video_url[:80]}{'...' if len(video_url) > 80 else ''}")
        logger.info(f"   └─ Подпись: {caption[:80]}{'...' if len(caption) > 80 else ''}")

        response = requests.post(
            _AYRSHARE_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.error(f"❌ Ayrshare ошибка {response.status_code}: {response.text}")
            raise

        result = response.json()
        logger.info(
            f"✅ Опубликовано: status={result.get('status')}, id={result.get('id')}"
        )
        return result
