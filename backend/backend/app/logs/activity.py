from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable, Optional
from pathlib import Path

from .structured import get_data_root


def _in_range(ts_iso: str, from_day: Optional[str], to_day: Optional[str]) -> bool:
    day = (ts_iso or '')[:10]
    if from_day and day < from_day:
        return False
    if to_day and day > to_day:
        return False
    return True


def stream_csv(from_day: str | None, to_day: str | None) -> Iterable[bytes]:
    root = get_data_root()
    path = root / 'activity.log'
    # Header
    yield b"timestamp,user_id,email,event,job_id,meta_json\n"
    try:
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except Exception:
                    # Skip non-JSON lines
                    continue
                ts = evt.get('timestamp') or evt.get('ts') or ''
                if from_day or to_day:
                    if not _in_range(ts, from_day, to_day):
                        continue
                user_id = evt.get('user_id', '')
                email = evt.get('email', '')
                etype = evt.get('type') or evt.get('event') or ''
                job_id = evt.get('job_id', '')
                meta = evt.get('meta', {})
                try:
                    meta_json = json.dumps(meta, ensure_ascii=False)
                except Exception:
                    meta_json = '{}'
                # CSV escaping for simple fields (wrap in quotes, escape internal quotes)
                def esc(x: str) -> str:
                    x = str(x)
                    return '"' + x.replace('"', '""') + '"'
                row = [ts, str(user_id), email, etype, str(job_id), meta_json]
                csv_line = ','.join(esc(col) for col in row) + '\n'
                yield csv_line.encode('utf-8')
    except FileNotFoundError:
        # No activity log; caller decides 204 or fallback
        return
"""
Activity logging for render jobs.
Simple file-based JSONL logger for job lifecycle events.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# Activity log file location
ACTIVITY_LOG_DIR = Path("data")
ACTIVITY_LOG_FILE = ACTIVITY_LOG_DIR / "activity.log"


def log_event(
    job_id: str,
    event_type: str,
    message: str,
    meta: dict[str, Any] | None = None
) -> None:
    """
    Log an activity event for a job to JSONL file.
    
    Args:
        job_id: Job identifier
        event_type: Event type (job_created, tts_started, etc.)
        message: Human-readable message
        meta: Optional metadata dict
    """
    # Ensure log directory exists
    ACTIVITY_LOG_DIR.mkdir(exist_ok=True)
    
    # Create log entry
    entry = {
        "ts_iso": datetime.utcnow().isoformat() + "Z",
        "job_id": job_id,
        "event_type": event_type,
        "message": message,
        "meta": meta or {}
    }
    
    # Append to JSONL file
    try:
        with open(ACTIVITY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        # Don't fail job on logging error
        print(f"Failed to log activity event: {e}")


def read_events(job_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """
    Read activity events for a specific job.
    
    Args:
        job_id: Job identifier
        limit: Maximum number of events to return
        
    Returns:
        List of event dicts, newest first
    """
    if not ACTIVITY_LOG_FILE.exists():
        return []
    
    events = []
    try:
        with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("job_id") == job_id:
                        events.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Failed to read activity log: {e}")
        return []
    
    # Return newest first
    events.reverse()
    return events[:limit]
