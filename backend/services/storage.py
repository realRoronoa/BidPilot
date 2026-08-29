"""Object storage service for uploaded PDF binaries.
Supports local filesystem storage (default) or AWS S3 (if S3_BUCKET is configured).
"""
import os
import mimetypes
from pathlib import Path

APP_NAME = "bidpilot"
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", Path(__file__).parent.parent / "data" / "storage"))
S3_BUCKET = os.environ.get("S3_BUCKET")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
    return _s3_client


def init_storage(force: bool = False):
    """Initialize storage subsystem (ensure local directory exists or S3 bucket is accessible)."""
    if S3_BUCKET:
        s3 = _get_s3_client()
        s3.head_bucket(Bucket=S3_BUCKET)
        return f"s3://{S3_BUCKET}"
    else:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        return str(STORAGE_DIR)


def put_object(path: str, data: bytes, content_type: str = "application/pdf") -> dict:
    """Store an object in local storage or S3."""
    init_storage()
    if S3_BUCKET:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=path,
            Body=data,
            ContentType=content_type,
        )
    else:
        file_path = STORAGE_DIR / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)

    return {"path": path, "size": len(data)}


def get_object(path: str):
    """Retrieve an object from local storage or S3."""
    init_storage()
    content_type = mimetypes.guess_type(path)[0] or "application/pdf"
    if S3_BUCKET:
        s3 = _get_s3_client()
        resp = s3.get_object(Bucket=S3_BUCKET, Key=path)
        content = resp["Body"].read()
        ctype = resp.get("ContentType", content_type)
        return content, ctype
    else:
        file_path = STORAGE_DIR / path
        if not file_path.exists():
            raise FileNotFoundError(f"Object not found: {path}")
        with open(file_path, "rb") as f:
            content = f.read()
        return content, content_type
