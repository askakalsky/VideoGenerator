"""
TikTok Content Posting API (official).
https://developers.tiktok.com/products/content-posting-api/

Setup:
1. Register at https://developers.tiktok.com
2. Create an app, enable "Content Posting API"
3. Run get_tiktok_oauth_token.py to authorize and get ACCESS_TOKEN + REFRESH_TOKEN
4. Set env vars: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN, TIKTOK_REFRESH_TOKEN

Notes:
- Until your app passes audit, videos are posted as PRIVATE (self_only).
- Audit is a form, not business verification — fill it at developers.tiktok.com
"""

import logging
import os

logger = logging.getLogger(__name__)

# TODO: implement after getting OAuth tokens from get_tiktok_oauth_token.py
raise NotImplementedError(
    "TikTok API poster not yet configured. "
    "Run get_tiktok_oauth_token.py first to get access tokens."
)


class TikTokAPIPoster:
    """Posts videos via official TikTok Content Posting API."""

    BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(self):
        self.client_key = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
        self.client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
        self.access_token = os.environ.get("TIKTOK_ACCESS_TOKEN", "").strip()
        self.refresh_token = os.environ.get("TIKTOK_REFRESH_TOKEN", "").strip()

        if not self.access_token:
            raise ValueError(
                "TIKTOK_ACCESS_TOKEN not set. "
                "Run get_tiktok_oauth_token.py to authorize."
            )

    def post(self, video_url: str, caption: str) -> dict:
        """
        Post a video to TikTok via Content Posting API.
        Video is posted from a public URL (R2 link).
        """
        # TODO: implement
        # 1. POST /v2/post/publish/video/init/
        #    body: { "post_info": { "title": caption, "privacy_level": "PUBLIC_TO_EVERYONE" },
        #            "source_info": { "source": "PULL_FROM_URL", "video_url": video_url } }
        # 2. Poll /v2/post/publish/status/fetch/ until status == "PUBLISH_COMPLETE"
        raise NotImplementedError("post() not yet implemented")

    def refresh_access_token(self) -> str:
        """Refresh expired access token using refresh_token."""
        # TODO: implement
        # POST https://open.tiktokapis.com/v2/oauth/token/
        # body: { grant_type: refresh_token, client_key, client_secret, refresh_token }
        raise NotImplementedError("refresh_access_token() not yet implemented")
