from __future__ import annotations
from typing import Any, Dict, List, Tuple

# Allowed keys
PLAN_KEYS = {"title", "voice_id", "template", "duration_sec", "scenes"}
SCENE_KEYS = {"script", "image_prompt", "duration_sec"}


def _to_number(val: Any, default: float) -> float:
    try:
        if val is None:
            return float(default)
        if isinstance(val, (int, float)):
            return float(val)
        return float(str(val).strip())
    except Exception:
        return float(default)


def normalize_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    p = dict(plan or {})
    out: Dict[str, Any] = {}
    out["title"] = p.get("title") or ""
    out["voice_id"] = p.get("voice_id") or ""
    out["template"] = p.get("template") or ""
    out["duration_sec"] = _to_number(p.get("duration_sec"), 30)
    scenes_in = p.get("scenes")
    if not isinstance(scenes_in, list):
        scenes_in = []
    scenes_out = []
    for s in scenes_in:
        s = dict(s or {}) if isinstance(s, dict) else {}
        scenes_out.append({
            "script": s.get("script") or s.get("text") or "",
            "image_prompt": s.get("image_prompt") or s.get("prompt") or "",
            "duration_sec": _to_number(s.get("duration_sec"), 2)
        })
    out["scenes"] = scenes_out
    return out


def validate_plan(plan: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    p = dict(plan or {})
    # Unknown plan keys
    for k in p.keys():
        if k not in PLAN_KEYS:
            warnings.append(f"Unknown plan key: {k}")
    # Title
    if not (p.get("title") or "").strip():
        warnings.append("Missing plan title")
    # Duration
    try:
        d = float(p.get("duration_sec", 0))
        if d <= 0:
            warnings.append("Plan duration_sec should be > 0")
    except Exception:
        warnings.append("Plan duration_sec is not a number")
    # Scenes
    scenes = p.get("scenes")
    if not isinstance(scenes, list) or len(scenes) == 0:
        warnings.append("Plan has no scenes")
        return warnings
    for idx, s in enumerate(scenes):
        if not isinstance(s, dict):
            warnings.append(f"Scene {idx+1}: not an object")
            continue
        for k in s.keys():
            if k not in SCENE_KEYS:
                warnings.append(f"Scene {idx+1}: unknown key {k}")
        try:
            d = float(s.get("duration_sec", 0))
            if d <= 0:
                warnings.append(f"Scene {idx+1}: duration_sec should be > 0")
        except Exception:
            warnings.append(f"Scene {idx+1}: duration_sec is not a number")
        if not (s.get("script") or "").strip():
            warnings.append(f"Scene {idx+1}: missing script")
    return warnings
