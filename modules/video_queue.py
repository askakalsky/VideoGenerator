"""
FIFO video posting queue backed by queue/queue.json in Cloudflare R2.

Generation adds videos to the end of the queue.
Posting takes the first item with status="ready" and marks it "posted".
"""

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_QUEUE_KEY = "queue/queue.json"


class VideoQueue:
    """FIFO queue for TikTok posting, persisted in R2 as JSON."""

    def __init__(self, r2):
        """
        Args:
            r2: R2Uploader instance
        """
        self.r2 = r2

    def push(self, url: str, caption: str) -> None:
        """
        Add a video to the end of the queue.

        Args:
            url: Public R2 URL of the video.
            caption: TikTok post caption.
        """
        data = self._load()
        data["items"].append(
            {
                "url": url,
                "caption": caption,
                "status": "ready",
                "created_at": datetime.utcnow().isoformat(),
                "posted_at": None,
            }
        )
        self._save(data)
        ready_count = sum(1 for i in data["items"] if i["status"] == "ready")
        logger.info(f"📥 Добавлено в очередь. Готовых к публикации: {ready_count}")

    def pop_next(self) -> Optional[Dict]:
        """
        Return the first ready item WITHOUT marking it posted yet.
        Call mark_posted(url) after successful posting.
        """
        data = self._load()
        for item in data["items"]:
            if item.get("status") == "ready":
                logger.info(f"📤 Взято из очереди: {item['url'][:80]}")
                return item

        logger.warning("⚠️  Очередь пуста — нет видео со статусом 'ready'")
        return None

    def mark_posted(self, url: str) -> None:
        """Mark item with given URL as posted after successful publish."""
        data = self._load()
        for item in data["items"]:
            if item.get("url") == url and item.get("status") == "ready":
                item["status"] = "posted"
                item["posted_at"] = datetime.utcnow().isoformat()
                self._save(data)
                logger.info("✅ Помечено как опубликованное")
                return

    def status(self) -> Dict:
        """Return queue stats: total, ready, posted."""
        data = self._load()
        items = data.get("items", [])
        return {
            "total": len(items),
            "ready": sum(1 for i in items if i.get("status") == "ready"),
            "posted": sum(1 for i in items if i.get("status") == "posted"),
        }

    def _load(self) -> Dict:
        """Download queue.json from R2. Returns empty queue if not found."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            self.r2.download(_QUEUE_KEY, tmp_path)

            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            tmp_path.unlink(missing_ok=True)
            return data

        except Exception:
            # Queue doesn't exist yet — start fresh
            return {"items": []}

    def _save(self, data: Dict) -> None:
        """Upload queue.json to R2."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp.name)

        try:
            self.r2.upload(tmp_path, _QUEUE_KEY)
        finally:
            tmp_path.unlink(missing_ok=True)
