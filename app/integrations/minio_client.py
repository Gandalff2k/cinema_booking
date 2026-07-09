import io
import json
import logging

from minio import Minio

from core.config import config

logger = logging.getLogger(__name__)

_PUBLIC_READ_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{config.MINIO_BUCKET}/*"],
        }
    ],
}


def get_client() -> Minio:
    return Minio(
        config.MINIO_ENDPOINT,
        access_key=config.MINIO_ROOT_USER,
        secret_key=config.MINIO_ROOT_PASSWORD,
        secure=config.MINIO_SECURE,
    )


def upload_poster(object_name: str, data: bytes, content_type: str) -> str:
    """Upload poster bytes and return the public path (`/media/movies/<name>`)."""
    client = get_client()
    if not client.bucket_exists(config.MINIO_BUCKET):
        client.make_bucket(config.MINIO_BUCKET)
        client.set_bucket_policy(config.MINIO_BUCKET, json.dumps(_PUBLIC_READ_POLICY))

    client.put_object(
        config.MINIO_BUCKET,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    logger.info("Uploaded poster %s (%d bytes)", object_name, len(data))
    return f"/media/{config.MINIO_BUCKET}/{object_name}"
