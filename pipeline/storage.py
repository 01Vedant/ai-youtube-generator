from pathlib import Path
import os
import logging
from typing import Optional, Dict

try:
    import boto3
    _HAS_BOTO = True
except Exception:
    _HAS_BOTO = False

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, s3_bucket: Optional[str] = None, s3_endpoint: Optional[str] = None, s3_key: Optional[str] = None, s3_secret: Optional[str] = None):
        self.s3_bucket = s3_bucket
        self.s3_endpoint = s3_endpoint
        self.s3_key = s3_key
        self.s3_secret = s3_secret
        self.s3_client = None
        if _HAS_BOTO and s3_bucket and s3_key and s3_secret:
            session = boto3.session.Session()
            params = dict(aws_access_key_id=s3_key, aws_secret_access_key=s3_secret)
            if s3_endpoint:
                params["endpoint_url"] = s3_endpoint
            self.s3_client = session.client("s3", **params)

    def upload_file(self, local_path: Path, remote_path: Optional[str] = None) -> Dict[str, str]:
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(local_path)
        if self.s3_client and self.s3_bucket:
            key = remote_path or local_path.name
            try:
                self.s3_client.upload_file(str(local_path), self.s3_bucket, key)
                url = f"s3://{self.s3_bucket}/{key}"
                return {"url": url, "key": key}
            except Exception as e:
                logger.warning("S3 upload failed, falling back to local: %s", e)
        out = {"url": str(local_path.resolve()), "path": str(local_path.resolve())}
        return out

    @staticmethod
    def ensure_dir(path: Path):
        path.mkdir(parents=True, exist_ok=True)
