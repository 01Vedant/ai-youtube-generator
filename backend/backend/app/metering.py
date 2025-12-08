"""
Metering: track usage per tenant (images, TTS, render, storage, uploads)
Quotas: enforce monthly caps with graceful degradation
"""

from typing import Dict, Optional
import json
import os
from datetime import datetime
from pathlib import Path
import redis
import logging

logger = logging.getLogger(__name__)

# Redis for real-time counters
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis unavailable for metering: {e}")
    redis_client = None

# Usage log directory
USAGE_LOG_DIR = Path(os.getenv("USAGE_LOG_DIR", "./platform/usage"))
USAGE_LOG_DIR.mkdir(parents=True, exist_ok=True)


class UsageCounter:
    """Track usage per tenant in Redis + append to monthly JSONL log."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.redis_key = f"usage:{tenant_id}:{datetime.utcnow().strftime('%Y%m')}"

    def increment(self, metric: str, amount: float = 1.0):
        """Increment a metric (images_count, tts_seconds, render_minutes, storage_mb, uploads_count)."""
        if redis_client:
            redis_client.hincrby(self.redis_key, metric, int(amount * 1000))  # Store as millis
            # Set 90-day TTL to auto-expire old months
            redis_client.expire(self.redis_key, 90 * 24 * 3600)

        # Append to monthly JSONL log
        log_file = USAGE_LOG_DIR / f"usage-{datetime.utcnow().strftime('%Y%m')}.jsonl"
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": self.tenant_id,
            "metric": metric,
            "amount": amount,
        }
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write usage log: {e}")

    def get_current_usage(self) -> Dict[str, float]:
        """Get current month usage for tenant."""
        if not redis_client:
            return {}

        data = redis_client.hgetall(self.redis_key)
        return {k: v / 1000.0 for k, v in data.items()}  # Convert from millis


class QuotaManager:
    """Enforce usage quotas per tenant."""

    # Default quotas (can be overridden by env vars or user tier)
    DEFAULT_QUOTAS = {
        "images_count": int(os.getenv("QUOTA_IMAGES_COUNT", "500")),
        "tts_seconds": int(os.getenv("QUOTA_TTS_SECONDS", "60000")),  # 1000 min
        "render_minutes": int(os.getenv("QUOTA_RENDER_MINUTES", "500")),
        "storage_mb": int(os.getenv("QUOTA_STORAGE_MB", "100000")),  # 100 GB
        "uploads_count": int(os.getenv("QUOTA_UPLOADS_COUNT", "100")),
    }

    def __init__(self, tenant_id: str, plan: str = "free"):
        """Initialize quota manager for tenant with given plan."""
        self.tenant_id = tenant_id
        self.plan = plan
        self.quotas = self._get_quotas_for_plan(plan)
        self.counter = UsageCounter(tenant_id)

    def _get_quotas_for_plan(self, plan: str) -> Dict[str, float]:
        """Get quotas based on user tier."""
        plan_multipliers = {
            "free": 1.0,
            "pro": 5.0,
            "enterprise": float("inf"),
        }
        multiplier = plan_multipliers.get(plan, 1.0)
        return {k: int(v * multiplier) for k, v in self.DEFAULT_QUOTAS.items()}

    def check_quota(self, metric: str, amount: float = 1.0) -> tuple[bool, Optional[str]]:
        """
        Check if usage + amount exceeds quota.
        Returns (allowed, message) tuple.
        """
        if metric not in self.quotas:
            logger.warning(f"Unknown metric: {metric}")
            return True, None

        usage = self.counter.get_current_usage()
        current = usage.get(metric, 0.0)
        quota = self.quotas[metric]

        if quota == float("inf"):  # Enterprise unlimited
            return True, None

        if current + amount > quota:
            percent = int((current / quota) * 100)
            msg = f"Usage quota exceeded for {metric} ({percent}% of {quota} limit). Please upgrade or wait until next month."
            return False, msg

        remaining = quota - current - amount
        return True, f"OK ({remaining}/{quota} remaining)"

    def enforce_quota(self, metric: str, amount: float = 1.0):
        """
        Check quota; raise 402 Payment Required if exceeded.
        """
        allowed, msg = self.check_quota(metric, amount)
        if not allowed:
            from fastapi import HTTPException
            raise HTTPException(status_code=402, detail=msg)
