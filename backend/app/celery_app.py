"""
Celery app configuration and task definitions for async pipeline.
"""

from celery import Celery

from app.config import settings

# Create Celery app
celery_app = Celery(
    "vibeanalytix",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],  # Explicitly import tasks module so they are registered
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=24 * 3600,  # 24 hours
)

# Configure beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-watchdog": {
        "task": "app.tasks.cleanup_watchdog",
        "schedule": settings.watchdog_interval_minutes * 60.0,
    },
}
