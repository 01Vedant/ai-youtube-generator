from __future__ import annotations

import os
from typing import Optional

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError


class S3Storage:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        bucket: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        endpoint_env = endpoint or os.getenv("STORAGE_ENDPOINT")
        self.bucket = (bucket or os.getenv("STORAGE_BUCKET") or "").strip()
        ak = access_key or os.getenv("STORAGE_ACCESS_KEY")
        sk = secret_key or os.getenv("STORAGE_SECRET_KEY")
        region_name = region or os.getenv("STORAGE_REGION")

        # Build client for S3/MinIO
        session = boto3.session.Session()
        self.client: BaseClient = session.client(
            "s3",
            endpoint_url=endpoint_env,
            region_name=region_name if region_name else None,
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
        )

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey"):
                return False
            raise

    def get_url(self, key: str, expires_sec: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_sec,
        )

    def put_file(self, key: str, src_path: str) -> None:
        self.client.upload_file(src_path, self.bucket, key)

    def list(self, prefix: str = "") -> list[str]:
        kwargs = {"Bucket": self.bucket}
        if prefix:
            kwargs["Prefix"] = prefix.lstrip("/")
        keys: list[str] = []
        resp = self.client.list_objects_v2(**kwargs)
        contents = resp.get("Contents", [])
        for obj in contents:
            k = obj.get("Key")
            if k:
                keys.append(k)
        return keys

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError:
            # silent on missing or errors
            pass
