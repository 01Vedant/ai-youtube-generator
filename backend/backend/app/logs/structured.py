from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_data_root() -> Path:
    # Resolve project root from this file, then ensure data directory exists
    # platform/backend/app/logs/structured.py -> project root is 4 parents up
    root = Path(__file__).resolve().parents[4]
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    return data


def get_log_dir() -> Path:
    logs = get_data_root() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def _safe(val: Any) -> Any:
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    try:
        return json.loads(json.dumps(val))  # if serializable, keep
    except Exception:
        return repr(val)


def log_json(event: str, **fields: Any) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"ts": ts, "level": "info", "event": event}
    for k, v in fields.items():
        payload[k] = _safe(v)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = get_log_dir() / f"app-{day}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
