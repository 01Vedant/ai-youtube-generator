from __future__ import annotations

import os
from functools import lru_cache

from .fs import FSStorage
from .s3 import S3Storage
from .base import Storage


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
        return S3Storage()
    return FSStorage()
