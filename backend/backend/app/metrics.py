"""
Prometheus metrics for render pipeline observability.
Counters: jobs_started, jobs_succeeded, jobs_failed
Histograms: job_duration_sec, step_duration_sec
Gauges: active_jobs
"""
import logging
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, Summary

logger = logging.getLogger(__name__)

# Global registry
_registry = CollectorRegistry()

# Counters
jobs_started = Counter(
    "jobs_started_total",
    "Total jobs started",
    registry=_registry,
)

jobs_succeeded = Counter(
    "jobs_succeeded_total",
    "Total jobs succeeded",
    registry=_registry,
)

jobs_failed = Counter(
    "jobs_failed_total",
    "Total jobs failed",
    labelnames=["error_type"],
    registry=_registry,
)

jobs_canceled = Counter(
    "jobs_canceled_total",
    "Total jobs canceled by user",
    registry=_registry,
)

# Histograms
job_duration_sec = Histogram(
    "job_duration_seconds",
    "Time to complete job (seconds)",
    buckets=(10, 30, 60, 120, 300, 600, 1800),
    registry=_registry,
)

step_duration_sec = Histogram(
    "step_duration_seconds",
    "Time per pipeline step (seconds)",
    labelnames=["step"],
    buckets=(1, 5, 10, 30, 60, 300),
    registry=_registry,
)

# Gauges
active_jobs = Gauge(
    "active_jobs",
    "Current number of running jobs",
    registry=_registry,
)

total_cost_estimated = Counter(
    "total_cost_estimated_usd",
    "Total estimated cost of all jobs (USD)",
    registry=_registry,
)

# Rate limit hits
rate_limit_hits = Counter(
    "rate_limit_hits_total",
    "Total rate limit rejections",
    labelnames=["endpoint"],
    registry=_registry,
)

# Quota violations
quota_violations = Counter(
    "quota_violations_total",
    "Total quota violations",
    labelnames=["quota_type"],
    registry=_registry,
)

# Queue and resource gauges
queue_depth = Gauge(
    "queue_depth",
    "Current render queue depth",
    registry=_registry,
)

gpu_in_use = Gauge(
    "gpu_in_use",
    "GPU currently in use (0 or 1)",
    registry=_registry,
)

disk_free_gb = Gauge(
    "disk_free_gb",
    "Free disk space in GB",
    registry=_registry,
)

# Preflight and provider check histograms
preflight_duration_ms = Histogram(
    "preflight_duration_milliseconds",
    "Preflight check duration in milliseconds",
    labelnames=["check"],
    buckets=(10, 50, 100, 250, 500, 1000, 2000),
    registry=_registry,
)

provider_check_ms = Histogram(
    "provider_check_milliseconds",
    "Provider API check duration in milliseconds",
    labelnames=["provider"],
    buckets=(10, 50, 100, 250, 500, 1000, 2000),
    registry=_registry,
)

# Error budget counters
job_timeouts_total = Counter(
    "job_timeouts_total",
    "Total jobs that exceeded runtime limit",
    registry=_registry,
)

provider_429_total = Counter(
    "provider_429_total",
    "Total 429 rate limit responses from providers",
    labelnames=["provider"],
    registry=_registry,
)

youtube_fail_total = Counter(
    "youtube_fail_total",
    "Total YouTube upload failures",
    labelnames=["reason"],
    registry=_registry,
)


def get_registry():
    """Get Prometheus registry."""
    return _registry

# Lightweight counters/summaries required by spec
renders_started_total = Counter(
    "renders_started_total",
    "Number of renders started",
    registry=_registry,
)

renders_completed_total = Counter(
    "renders_completed_total",
    "Number of renders completed",
    registry=_registry,
)

renders_failed_total = Counter(
    "renders_failed_total",
    "Number of renders failed",
    registry=_registry,
)

tts_seconds_total = Summary(
    "tts_seconds_total",
    "Accumulated TTS seconds",
    registry=_registry,
)

# Optional polish for crash-safe queue
jobs_requeued_stale_total = Counter(
    "jobs_requeued_stale_total",
    "Jobs requeued due to stale heartbeat",
    registry=_registry,
)

job_queue_running = Gauge(
    "job_queue_running",
    "Currently running jobs count",
    registry=_registry,
)


def inc_renders_started(n: int = 1) -> None:
    try:
        for _ in range(max(0, n)):
            renders_started_total.inc()
    except Exception:
        pass


def inc_renders_completed(n: int = 1) -> None:
    try:
        for _ in range(max(0, n)):
            renders_completed_total.inc()
    except Exception:
        pass


def inc_renders_failed(n: int = 1) -> None:
    try:
        for _ in range(max(0, n)):
            renders_failed_total.inc()
    except Exception:
        pass


def add_tts_seconds(sec: float) -> None:
    try:
        tts_seconds_total.observe(float(sec))
    except Exception:
        pass


def inc_jobs_requeued_stale(n: int) -> None:
    try:
        if n:
            jobs_requeued_stale_total.inc(n)
    except Exception:
        pass


def update_running_gauge() -> None:
    try:
        from app.db import get_conn
        conn = get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM job_queue WHERE status='running'").fetchone()
            job_queue_running.set(int(row["c"]))
        finally:
            conn.close()
    except Exception:
        pass
