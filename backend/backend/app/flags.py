from __future__ import annotations

import os
import json
from typing import Dict

_overrides: Dict[str, bool] = {}

def _env_defaults() -> Dict[str, bool]:
    raw = os.getenv('FEATURE_FLAGS', '')
    if not raw:
        return {}
    raw = raw.strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return {str(k): bool(v) for k, v in obj.items()}
    except Exception:
        pass
    # comma list
    defaults: Dict[str, bool] = {}
    for k in raw.split(','):
        k = k.strip()
        if k:
            defaults[k] = True
    return defaults

def get_flags() -> Dict[str, bool]:
    base = _env_defaults()
    base.update(_overrides)
    return base

def set_flag(key: str, val: bool) -> Dict[str, bool]:
    _overrides[str(key)] = bool(val)
    return get_flags()

def is_enabled(key: str) -> bool:
    return bool(get_flags().get(key, False))
