"""
Celery task definitions for DevotionalAI Platform
Demo tasks for testing queue functionality
"""

from app.celery_config import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.echo")
def echo(x):
    """Demo task: echoes input back"""
    logger.info(f"Echo task received: {x}")
    return x


@celery_app.task(name="app.health_check")
def health_check():
    """Demo task: health check for queue system"""
    logger.info("Health check task executed")
    return {"status": "ok", "message": "Queue is healthy"}
