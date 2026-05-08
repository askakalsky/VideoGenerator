"""
TikTok video posting via tiktok-uploader.
Tries multiple auth methods: Netscape cookies file, cookies_list, sessionid only.
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
        self.session_id = os.environ.get("TIKTOK_SESSION_ID", "").strip()
        if not self.cookies_json and not self.session_id:
            raise ValueError("TIKTOK_COOKIES or TIKTOK_SESSION_ID must be set")

    def post(self, video_url: str, caption: str) -> dict:
        from tiktok_uploader.upload import upload_video
        from tiktok_uploader.auth import AuthBackend

        tmp_video = Path(tempfile.mktemp(suffix=".mp4"))
        tmp_cookies = Path(tempfile.mktemp(suffix=".txt"))
        try:
            self._download(video_url, tmp_video)
            logger.info(f"Posting to TikTok: {caption[:80]}")

            auth = self._build_auth(tmp_cookies)
            failed = upload_video(str(tmp_video), description=caption, auth=auth)

            if failed:
                raise RuntimeError(f"TikTok upload failed: {failed}")

            logger.info("Posted to TikTok successfully")
            return {"status": "success"}

        finally:
            for p in (tmp_video, tmp_cookies):
                if p.exists():
                    p.unlink()

    def _build_auth(self, tmp_cookies: Path):
        from tiktok_uploader.auth import AuthBackend

        # Method 1: Netscape cookies file from JSON
        if self.cookies_json:
            try:
                cookies = json.loads(self.cookies_json)
                netscape = self._to_netscape(cookies)
                tmp_cookies.write_text(netscape, encoding="utf-8")
                logger.info("Using Netscape cookies file auth")
                return AuthBackend(cookies=str(tmp_cookies))
            except Exception as e:
                logger.warning(f"Netscape auth build failed: {e}, falling back")

        # Method 2: sessionid only
        if self.session_id:
            logger.info("Using sessionid cookies_list auth")
            return AuthBackend(cookies_list=[{
                "name": "sessionid",
                "value": self.session_id,
                "domain": ".tiktok.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
            }])

        raise ValueError("No valid TikTok auth method available")

    def _to_netscape(self, cookies: list) -> str:
        lines = ["# Netscape HTTP Cookie File"]
        for c in cookies:
            domain = c.get("domain", ".tiktok.com")
            include_sub = "TRUE" if domain.startswith(".") else "FALSE"
            path = c.get("path", "/")
            secure = "TRUE" if c.get("secure", False) else "FALSE"
            expiry = int(c.get("expires", 0) or 0)
            name = c.get("name", "")
            value = c.get("value", "")
            lines.append(f"{domain}\t{include_sub}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
        return "\n".join(lines)

    def _download(self, url: str, dest: Path) -> None:
        logger.info(f"Downloading video from R2: {url[:80]}")
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        size_mb = round(dest.stat().st_size / 1024 / 1024, 1)
        logger.info(f"Downloaded {size_mb} MB -> {dest.name}")
