"""
Cloudflare R2 storage integration via boto3 S3-compatible API.
"""

import logging
import os
from pathlib import Path
from typing import List

import boto3
from botocore.client import Config

logger = logging.getLogger(__name__)


class R2Uploader:
    """Upload/download files to/from Cloudflare R2."""

    def __init__(self):
        account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip()
        access_key = os.environ["CLOUDFLARE_R2_ACCESS_KEY_ID"].strip()
        secret_key = os.environ["CLOUDFLARE_R2_SECRET_ACCESS_KEY"].strip()
        self.bucket = os.environ["CLOUDFLARE_R2_BUCKET_NAME"].strip()
        self.public_url_base = os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", "").strip().rstrip("/")

        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    def upload(self, local_path: Path, key: str) -> str:
        """
        Upload a file to R2 and return its public URL.

        Args:
            local_path: Local file path.
            key: R2 object key (e.g. "videos/2025-05-06/Part_1.mp4").

        Returns:
            Public URL if CLOUDFLARE_R2_PUBLIC_URL is set, else empty string.
        """
        local_path = Path(local_path)
        logger.info(f"☁️  R2 upload: {local_path.name} → {key}")
        self.client.upload_file(
            Filename=str(local_path),
            Bucket=self.bucket,
            Key=key,
        )
        url = f"{self.public_url_base}/{key}" if self.public_url_base else ""
        logger.info(f"   └─ URL: {url or key}")
        return url

    def download(self, key: str, local_path: Path) -> Path:
        """
        Download a file from R2.

        Args:
            key: R2 object key.
            local_path: Destination path on disk.

        Returns:
            The local path.
        """
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"☁️  R2 download: {key} → {local_path.name}")
        self.client.download_file(
            Bucket=self.bucket,
            Key=key,
            Filename=str(local_path),
        )
        return local_path

    def list_objects(self, prefix: str = "") -> List[str]:
        """
        List object keys under a prefix.

        Args:
            prefix: Key prefix to filter (e.g. "stock_videos/").

        Returns:
            List of object keys.
        """
        keys = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def file_exists(self, key: str) -> bool:
        """Check if a key exists in the bucket."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False
