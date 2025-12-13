from __future__ import annotations

import os
from functools import lru_cache

from .fs import FSStorage
from .base import Storage

MISSING_BOTO3_MSG = "S3 storage selected but boto3 is not installed. Install boto3 or switch to FS storage."


def _has_s3_env() -> bool:
    required = [
        "STORAGE_ENDPOINT",
        "STORAGE_BUCKET",
        "STORAGE_ACCESS_KEY",
        "STORAGE_SECRET_KEY",
    ]
    return all(os.getenv(k) for k in required)


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    if _has_s3_env():
        try:
            from .s3 import S3Storage
        except ImportError as e:
            raise RuntimeError(MISSING_BOTO3_MSG) from e
        try:
            return S3Storage()
        except ImportError as e:
            raise RuntimeError(MISSING_BOTO3_MSG) from e
    return FSStorage()
