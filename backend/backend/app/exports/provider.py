from __future__ import annotations
from typing import Literal, Optional, Dict, List
from pathlib import Path
import json
import uuid
from datetime import datetime

ExportVisibility = Literal["public", "unlisted", "private"]


class ExportResult(dict):
    pass


class YouTubeProvider:
    def __init__(self, simulate: bool = True, exports_root: Optional[Path] = None):
        self.simulate = simulate
        self.exports_root = exports_root or (Path(__file__).resolve().parents[2] / "data" / "exports")
        self.exports_root.mkdir(parents=True, exist_ok=True)

    def upload(
        self,
        *,
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        visibility: ExportVisibility,
        user_id: str | None = None,
    ) -> ExportResult:
        # Simulate an upload by writing a JSON record and returning a fake URL
        export_id = uuid.uuid4().hex[:12]
        youtube_url = f"https://youtube.com/watch?v=mock-{export_id}"

        record = {
            "export_id": export_id,
            "provider": "youtube",
            "status": "completed" if self.simulate else "queued",
            "youtube_url": youtube_url,
            "user_id": user_id,
            "meta": {
                "title": title,
                "description": description,
                "tags": tags,
                "visibility": visibility,
                "video_path": video_path,
                "ts": datetime.utcnow().isoformat() + "Z",
            },
        }

        out_path = self.exports_root / f"{export_id}.json"
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        return ExportResult(record)
