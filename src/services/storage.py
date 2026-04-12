"""
DigitalOcean Spaces storage service.

Uses the S3-compatible boto3 client to upload and delete product images.
All settings come from environment variables — no values are hard-coded.
"""

from __future__ import annotations

import boto3

from src.core.config import get_settings

# Allowed MIME types and their canonical file extensions.
# These are pure constants — no settings access needed at import time.
ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB


class StorageService:
    """Handles uploads and deletions on DigitalOcean Spaces (S3-compatible)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.SPACES_BUCKET
        self._cdn_base = settings.SPACES_CDN_ENDPOINT.rstrip("/")
        self._client = boto3.client(
            "s3",
            region_name=settings.SPACES_REGION,
            endpoint_url=settings.SPACES_ENDPOINT,
            aws_access_key_id=settings.SPACES_KEY,
            aws_secret_access_key=settings.SPACES_SECRET,
        )

    def upload(self, data: bytes, key: str, content_type: str) -> str:
        """Upload *data* under *key* and return the CDN public URL."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ACL="public-read",
        )
        return f"{self._cdn_base}/{key}"

    def delete(self, key: str) -> None:
        """Delete the object at *key* from Spaces."""
        self._client.delete_object(
            Bucket=self._bucket,
            Key=key,
        )

    def url_to_key(self, url: str) -> str:
        """Extract the storage key from a CDN URL."""
        return url.removeprefix(f"{self._cdn_base}/")

    @staticmethod
    def ext_for(content_type: str) -> str:
        """Return the file extension for a supported MIME type."""
        return _MIME_TO_EXT[content_type]
