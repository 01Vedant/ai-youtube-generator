from __future__ import annotations
from fastapi import HTTPException, status
from .entitlements import has_feature

def require_feature(plan_id: str, feature: str) -> None:
    if not has_feature(plan_id, feature):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": {"code": "FEATURE_LOCKED", "feature": feature}},
        )
