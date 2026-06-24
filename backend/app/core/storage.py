# =============================================================================
# Jersey Ice Cream Platform — MinIO Object Storage Wrapper
# =============================================================================
# S3-compatible object storage for cart photos, model artifacts, and exports.
#
# Design Decision:
#   MinIO over direct filesystem because:
#   1. S3-compatible — zero code changes to migrate to AWS S3
#   2. Erasure coding provides data durability
#   3. Horizontal scaling via distributed mode
#   4. Built-in versioning for model artifacts
#
# File Upload Security:
#   - File type validation (magic bytes, not just extension)
#   - File size limits (10MB for photos, 500MB for model artifacts)
#   - Unique object names (UUID-based) to prevent overwrites
#   - Pre-signed URLs for secure temporary access
# =============================================================================

from __future__ import annotations

import io
import logging
import uuid
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.config import get_settings
from app.core.exceptions import StorageError

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Allowed File Types ─────────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}

MAX_PHOTO_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_MODEL_SIZE_BYTES = 500 * 1024 * 1024  # 500MB

# Magic bytes for file type validation
MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",  # WebP starts with RIFF
}


# ─── Storage Client ─────────────────────────────────────────────────────────


class ObjectStorage:
    """
    MinIO/S3 object storage client with secure upload/download operations.

    Responsibilities:
        - Upload cart photos with type/size validation
        - Generate pre-signed URLs for secure temporary access
        - Store and retrieve model artifacts
        - Export management (reports, CSV downloads)
    """

    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        self._initialized = False

    async def initialize(self) -> None:
        """Create required buckets if they don't exist."""
        buckets = [
            settings.minio_bucket_cart_photos,
            settings.minio_bucket_model_artifacts,
            "exports",
        ]
        for bucket in buckets:
            try:
                if not self._client.bucket_exists(bucket):
                    self._client.make_bucket(bucket)
                    logger.info("Created bucket: %s", bucket)
            except S3Error as e:
                logger.error("Failed to initialize bucket %s: %s", bucket, e)
        self._initialized = True

    def _validate_image(self, file_data: bytes, content_type: str) -> str:
        """
        Validate image file by magic bytes and content type.

        Returns the validated content type.
        Raises StorageError if validation fails.
        """
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise StorageError(
                operation="upload",
                details={"error": f"Unsupported content type: {content_type}"},
            )

        if len(file_data) > MAX_PHOTO_SIZE_BYTES:
            raise StorageError(
                operation="upload",
                details={
                    "error": f"File too large: {len(file_data)} bytes (max: {MAX_PHOTO_SIZE_BYTES})"
                },
            )

        if len(file_data) < 4:
            raise StorageError(
                operation="upload",
                details={"error": "File too small to be a valid image"},
            )

        # Validate magic bytes
        detected_type = None
        for magic, mime_type in MAGIC_BYTES.items():
            if file_data[: len(magic)] == magic:
                detected_type = mime_type
                break

        if detected_type and detected_type != content_type:
            # Allow HEIC/HEIF since their magic bytes are complex
            if content_type not in ("image/heic", "image/heif"):
                raise StorageError(
                    operation="upload",
                    details={
                        "error": f"Content type mismatch: declared {content_type}, detected {detected_type}"
                    },
                )

        return content_type

    def upload_cart_photo(
        self,
        file_data: bytes,
        content_type: str,
        cart_id: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """
        Upload a cart photo with validation.

        Args:
            file_data: Raw file bytes
            content_type: MIME type
            cart_id: Cart UUID for organizing storage
            metadata: Optional metadata to attach

        Returns:
            dict with storage_key, storage_url, and object info
        """
        validated_type = self._validate_image(file_data, content_type)
        extension = ALLOWED_IMAGE_TYPES[validated_type]

        # Generate unique object key: cart_id/YYYY/MM/DD/uuid.ext
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        object_key = (
            f"{cart_id}/{now.strftime('%Y/%m/%d')}/{uuid.uuid4()}{extension}"
        )

        try:
            self._client.put_object(
                bucket_name=settings.minio_bucket_cart_photos,
                object_name=object_key,
                data=io.BytesIO(file_data),
                length=len(file_data),
                content_type=validated_type,
                metadata=metadata or {},
            )

            logger.info(
                "Uploaded cart photo: bucket=%s key=%s size=%d",
                settings.minio_bucket_cart_photos,
                object_key,
                len(file_data),
            )

            return {
                "storage_key": object_key,
                "bucket": settings.minio_bucket_cart_photos,
                "size_bytes": len(file_data),
                "content_type": validated_type,
            }
        except S3Error as e:
            logger.error("Failed to upload cart photo: %s", e)
            raise StorageError(operation="upload", details={"s3_error": str(e)})

    def get_presigned_url(
        self,
        bucket: str,
        object_key: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """
        Generate a pre-signed URL for temporary read access.

        Used for:
        - Serving cart photos to the dashboard
        - Downloading model artifacts
        - Exporting reports

        Security: URL is time-limited and includes a signature.
        """
        try:
            return self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_key,
                expires=expires,
            )
        except S3Error as e:
            logger.error("Failed to generate presigned URL: %s", e)
            raise StorageError(
                operation="presign",
                details={"bucket": bucket, "key": object_key, "error": str(e)},
            )

    def download_object(self, bucket: str, object_key: str) -> bytes:
        """Download an object's contents."""
        try:
            response = self._client.get_object(bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error("Failed to download object %s/%s: %s", bucket, object_key, e)
            raise StorageError(
                operation="download",
                details={"bucket": bucket, "key": object_key, "error": str(e)},
            )

    def delete_object(self, bucket: str, object_key: str) -> bool:
        """Delete an object from storage."""
        try:
            self._client.remove_object(bucket, object_key)
            return True
        except S3Error as e:
            logger.error("Failed to delete object %s/%s: %s", bucket, object_key, e)
            return False

    def upload_model_artifact(
        self,
        file_path: str,
        model_name: str,
        version: str,
    ) -> dict[str, str]:
        """
        Upload a trained model artifact.

        Object key: models/{model_name}/{version}/{filename}
        """
        import os

        filename = os.path.basename(file_path)
        object_key = f"models/{model_name}/{version}/{filename}"

        file_size = os.path.getsize(file_path)
        if file_size > MAX_MODEL_SIZE_BYTES:
            raise StorageError(
                operation="upload_model",
                details={"error": f"Model file too large: {file_size} bytes"},
            )

        try:
            self._client.fput_object(
                bucket_name=settings.minio_bucket_model_artifacts,
                object_name=object_key,
                file_path=file_path,
                metadata={"model_name": model_name, "version": version},
            )

            logger.info("Uploaded model artifact: %s (v%s)", model_name, version)
            return {
                "storage_key": object_key,
                "bucket": settings.minio_bucket_model_artifacts,
                "size_bytes": file_size,
            }
        except S3Error as e:
            logger.error("Failed to upload model: %s", e)
            raise StorageError(operation="upload_model", details={"error": str(e)})


# ─── Singleton ───────────────────────────────────────────────────────────────

_storage: ObjectStorage | None = None


def get_object_storage() -> ObjectStorage:
    """Get or create the singleton object storage client."""
    global _storage
    if _storage is None:
        _storage = ObjectStorage()
    return _storage


async def check_storage_health() -> dict:
    """Verify MinIO connectivity."""
    import time

    start = time.monotonic()
    try:
        storage = get_object_storage()
        # List buckets as a health check
        buckets = storage._client.list_buckets()
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "buckets": [b.name for b in buckets],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
