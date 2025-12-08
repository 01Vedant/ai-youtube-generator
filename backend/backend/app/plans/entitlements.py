from __future__ import annotations
from typing import TypedDict, Dict, Set

class PlanSpec(TypedDict):
    name: str
    quotas: Dict[str, int]
    features: Set[str]

PLANS: Dict[str, PlanSpec] = {
    "free": {
        "name": "Free",
        "quotas": {"renders_per_day": 10, "tts_sec_per_day": 900},
        "features": {"share_links"},
    },
    "pro": {
        "name": "Pro",
        "quotas": {"renders_per_day": 50, "tts_sec_per_day": 7200},
        "features": {"share_links", "youtube_export", "s3_urls"},
    },
}

def get_plan_spec(plan_id: str) -> PlanSpec:
    pid = plan_id or "free"
    return PLANS.get(pid, PLANS["free"])  # default to free if unknown

def has_feature(plan_id: str, feature: str) -> bool:
    spec = get_plan_spec(plan_id)
    return feature in spec["features"]

def quota_for(plan_id: str, key: str, default: int) -> int:
    spec = get_plan_spec(plan_id)
    return int(spec["quotas"].get(key, default))
