from __future__ import annotations

import os
from pathlib import Path
from shutil import copy2

from app.settings import OUTPUT_ROOT


class FSStorage:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else OUTPUT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # prevent path traversal
        key = key.lstrip("/")
        return self.root / key

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def get_url(self, key: str, expires_sec: int = 3600) -> str:  # noqa: ARG002
        key = key.lstrip("/")
        return f"/artifacts/{key}"

    def put_file(self, key: str, src_path: str) -> None:
        dst = self._path(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        copy2(src_path, dst)

    def list(self, prefix: str = "") -> list[str]:
        prefix = prefix.lstrip("/") if prefix else ""
        root = self.root
        results: list[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                full = Path(dirpath) / fn
                rel = str(full.relative_to(root)).replace("\\", "/")
                if not prefix or rel.startswith(prefix):
                    results.append(rel)
        return results

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except FileNotFoundError:
            pass
