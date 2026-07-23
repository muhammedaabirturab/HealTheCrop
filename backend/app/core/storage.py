"""
Object storage wrapper. Prefers MinIO (S3-compatible local cloud storage) and
transparently falls back to local-disk storage under LOCAL_STORAGE_FALLBACK_DIR
when MinIO is unreachable (e.g. during local development without Docker
running), so the upload/prediction flows keep working end-to-end either way.
"""
import io
import logging
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageService:
    def __init__(self):
        self._client = None
        self._minio_available = False
        self._init_minio()

    def _init_minio(self):
        try:
            from minio import Minio

            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            for bucket in (settings.MINIO_BUCKET_IMAGES, settings.MINIO_BUCKET_REPORTS):
                if not self._client.bucket_exists(bucket):
                    self._client.make_bucket(bucket)
            self._minio_available = True
            logger.info("Connected to MinIO at %s", settings.MINIO_ENDPOINT)
        except Exception as exc:  # noqa: BLE001 - any connectivity issue triggers fallback
            logger.warning("MinIO unavailable (%s); using local disk fallback storage", exc)
            self._minio_available = False

    def _local_path(self, bucket: str, object_name: str) -> Path:
        path = Path(settings.LOCAL_STORAGE_FALLBACK_DIR) / bucket / object_name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def upload_bytes(self, bucket: str, data: bytes, extension: str = "") -> str:
        object_name = f"{uuid.uuid4().hex}{extension}"
        if self._minio_available:
            try:
                self._client.put_object(bucket, object_name, io.BytesIO(data), length=len(data))
                return f"minio://{bucket}/{object_name}"
            except Exception as exc:  # noqa: BLE001
                logger.warning("MinIO upload failed (%s); falling back to disk", exc)
        self._local_path(bucket, object_name).write_bytes(data)
        return f"local://{bucket}/{object_name}"

    def get_bytes(self, object_key: str) -> Optional[bytes]:
        scheme, rest = object_key.split("://", 1)
        bucket, object_name = rest.split("/", 1)
        if scheme == "minio" and self._minio_available:
            response = self._client.get_object(bucket, object_name)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        path = self._local_path(bucket, object_name)
        return path.read_bytes() if path.exists() else None

    @property
    def status(self) -> str:
        return "minio" if self._minio_available else "local_disk_fallback"


storage_service = StorageService()
