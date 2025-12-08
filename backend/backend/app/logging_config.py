"""
Structured logging with request_id, job_id correlation and secret scrubbing.
"""
import logging
import json
import re
import sys
from pythonjsonlogger import jsonlogger

# Patterns to scrub from logs
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*(["\']?)([^\s"\']+)\2', r'\1=***'),
    (r'(?i)(openai|elevenlabs|token|password)\s*[:=]\s*(["\']?)([^\s"\']+)\2', r'\1=***'),
    (r'(?i)(authorization|bearer)\s*[:=]\s*(["\']?)([^\s"\']+)\2', r'\1=***'),
]


class SecretScrubber(logging.Filter):
    """Filter that scrubs secrets from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Scrub secrets from message and args."""
        if isinstance(record.msg, str):
            record.msg = self._scrub(record.msg)
        
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._scrub(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._scrub(str(arg)) for arg in record.args)
        
        return True

    @staticmethod
    def _scrub(text: str) -> str:
        """Scrub secrets from text."""
        for pattern, replacement in SECRET_PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text


class JSONFormatter(jsonlogger.JsonFormatter):
    """JSON formatter with request_id and job_id injection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to JSON log."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        
        # Add correlation IDs from request scope if available
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        
        if hasattr(record, "job_id"):
            log_record["job_id"] = record.job_id


def setup_logging(debug: bool = False, json_logs: bool = True):
    """
    Configure structured logging with optional JSON formatting.
    
    Args:
        debug: Enable debug level logging
        json_logs: Use JSON format (production) vs. pretty format (dev)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Create formatter
    if json_logs:
        formatter = JSONFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)

    # Add secret scrubber
    scrubber = SecretScrubber()
    handler.addFilter(scrubber)

    root_logger.addHandler(handler)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized (json=%s, debug=%s)", json_logs, debug)
    return logger


def create_logger_with_context(name: str, request_id: str = None, job_id: str = None):
    """
    Create logger with injected correlation IDs.
    
    Usage:
        logger = create_logger_with_context(__name__, request_id=req_id, job_id=job_id)
        logger.info("Processing job")
    """
    logger = logging.getLogger(name)
    
    if request_id:
        logger.request_id = request_id
    if job_id:
        logger.job_id = job_id
    
    return logger
