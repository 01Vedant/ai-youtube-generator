"""
Logging and metrics infrastructure for the rendering pipeline.
Provides structured logging per-job and Prometheus-compatible metrics.
"""
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """Simple metrics collector."""
    jobs_started: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    total_duration: float = 0.0
    image_errors: int = 0
    tts_errors: int = 0
    upload_errors: int = 0
    youtube_uploads: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "jobs_started": self.jobs_started,
            "jobs_completed": self.jobs_completed,
            "jobs_failed": self.jobs_failed,
            "total_duration_seconds": self.total_duration,
            "image_errors": self.image_errors,
            "tts_errors": self.tts_errors,
            "upload_errors": self.upload_errors,
            "youtube_uploads": self.youtube_uploads,
            "success_rate": (
                self.jobs_completed / self.jobs_started * 100
                if self.jobs_started > 0
                else 0
            ),
        }

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = [
            f"# HELP bhakti_jobs_started Total jobs started",
            f"# TYPE bhakti_jobs_started counter",
            f"bhakti_jobs_started {self.jobs_started}",
            f"",
            f"# HELP bhakti_jobs_completed Total jobs completed successfully",
            f"# TYPE bhakti_jobs_completed counter",
            f"bhakti_jobs_completed {self.jobs_completed}",
            f"",
            f"# HELP bhakti_jobs_failed Total jobs failed",
            f"# TYPE bhakti_jobs_failed counter",
            f"bhakti_jobs_failed {self.jobs_failed}",
            f"",
            f"# HELP bhakti_total_duration_seconds Total processing time",
            f"# TYPE bhakti_total_duration_seconds counter",
            f"bhakti_total_duration_seconds {self.total_duration}",
            f"",
            f"# HELP bhakti_errors_total Total errors by type",
            f"# TYPE bhakti_errors_total counter",
            f'bhakti_errors_total{{type="image"}} {self.image_errors}',
            f'bhakti_errors_total{{type="tts"}} {self.tts_errors}',
            f'bhakti_errors_total{{type="upload"}} {self.upload_errors}',
        ]
        return "\n".join(lines)


# Global metrics instance
_metrics = Metrics()


def get_metrics() -> Metrics:
    """Get global metrics instance."""
    return _metrics


def setup_logging(job_id: str, output_dir: Path) -> logging.Logger:
    """
    Setup per-job logger that writes to both console and file.
    
    Args:
        job_id: Unique job identifier
        output_dir: Directory to write logs to
        
    Returns:
        Configured logger instance
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(f"bhakti.{job_id}")
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler
    log_file = output_dir / "job.log"
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Console handler (less verbose)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter with timestamps
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    logger.info(f"=== Job {job_id} started at {datetime.now().isoformat()} ===")
    
    return logger


class JobLogger:
    """Context manager for job-scoped logging and error tracking."""
    
    def __init__(self, job_id: str, output_dir: Path):
        self.job_id = job_id
        self.output_dir = Path(output_dir)
        self.logger = setup_logging(job_id, output_dir)
        self.errors: Dict[str, list] = {
            "image": [],
            "tts": [],
            "upload": [],
            "other": [],
        }
        self.start_time = time.time()
        self.metrics = get_metrics()
        self.metrics.jobs_started += 1
    
    def log_error(self, category: str, message: str, exception: Optional[Exception] = None):
        """Log an error and track it by category."""
        if category not in self.errors:
            category = "other"
        
        self.errors[category].append(message)
        self.logger.error(f"[{category}] {message}")
        if exception:
            self.logger.exception(exception)
        
        # Update global metrics
        if category in self.metrics.__dict__:
            setattr(self.metrics, f"{category}_errors", getattr(self.metrics, f"{category}_errors", 0) + 1)
    
    def log_success(self):
        """Log job success and update metrics."""
        duration = time.time() - self.start_time
        self.metrics.jobs_completed += 1
        self.metrics.total_duration += duration
        self.logger.info(f"=== Job {self.job_id} completed successfully in {duration:.1f}s ===")
    
    def log_failure(self, reason: str):
        """Log job failure and update metrics."""
        duration = time.time() - self.start_time
        self.metrics.jobs_failed += 1
        self.metrics.total_duration += duration
        self.logger.error(f"=== Job {self.job_id} failed after {duration:.1f}s: {reason} ===")
    
    def get_error_summary(self) -> Dict[str, list]:
        """Get all tracked errors by category."""
        return {k: v for k, v in self.errors.items() if v}
    
    def write_summary(self, summary: Dict[str, Any]):
        """Write job summary to file."""
        summary_file = self.output_dir / "job_summary.json"
        import json
        summary_file.write_text(json.dumps(summary, indent=2))
        self.logger.info(f"Summary written to {summary_file}")


def record_youtube_upload(success: bool):
    """Record YouTube upload attempt."""
    if success:
        get_metrics().youtube_uploads += 1


def get_metrics_dict() -> Dict[str, Any]:
    """Get current metrics as dict."""
    return get_metrics().to_dict()


def export_prometheus_metrics() -> str:
    """Export metrics in Prometheus format."""
    return get_metrics().to_prometheus()
