from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "pascalhub",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks", "app.worker.discovery_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "monitor-sources-every-15-minutes": {
            "task": "app.worker.tasks.monitor_sources",
            "schedule": 900.0,
        },
        "nightly-benchmark": {
            "task": "app.worker.tasks.nightly_benchmark",
            "schedule": crontab(hour=2, minute=0),  # 02:00 UTC every night
        },
        "scheduled-discovery-every-6-hours": {
            "task": "app.worker.tasks.scheduled_discovery",
            "schedule": settings.DISCOVERY_INTERVAL_HOURS * 3600,
        },
        "retest-discovered-sources-daily": {
            "task": "app.worker.tasks.retest_discovered_sources",
            "schedule": 86400.0,
        },
        "deep-discovery-nightly": {
            "task": "app.worker.tasks.deep_discovery",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)
