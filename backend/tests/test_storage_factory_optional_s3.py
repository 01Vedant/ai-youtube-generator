import builtins
import importlib
import sys

from app.artifacts_storage import factory
from app.artifacts_storage.fs import FSStorage


def test_import_main_without_boto3_when_s3_disabled(monkeypatch):
    # Force filesystem storage selection
    for key in ("STORAGE_ENDPOINT", "STORAGE_BUCKET", "STORAGE_ACCESS_KEY", "STORAGE_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)

    for mod in ("boto3", "botocore", "botocore.client", "botocore.exceptions"):
        monkeypatch.delitem(sys.modules, mod, raising=False)

    real_import = builtins.__import__

    def _block_boto3(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(("boto3", "botocore")):
            raise ImportError("boto3 unavailable for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _block_boto3)
    factory.get_storage.cache_clear()
    monkeypatch.delitem(sys.modules, "backend.backend.main", raising=False)

    try:
        importlib.import_module("backend.backend.main")
        storage = factory.get_storage()
        assert isinstance(storage, FSStorage)
        assert "boto3" not in sys.modules
        assert "botocore" not in sys.modules
    finally:
        factory.get_storage.cache_clear()
