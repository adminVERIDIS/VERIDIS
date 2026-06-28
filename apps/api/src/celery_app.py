from __future__ import annotations

import os

from celery import Celery


def _broker_url() -> str:
    return os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"


def _result_backend() -> str:
    return os.getenv("CELERY_RESULT_BACKEND") or os.getenv("REDIS_URL") or "redis://localhost:6379/1"


celery_app = Celery(
    "veridis",
    broker=_broker_url(),
    backend=_result_backend(),
    include=["workers.generate_pdf"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=900,
    task_soft_time_limit=840,
    timezone="Europe/Paris",
    beat_schedule={
        "analytics-alerts-hourly": {
            "task": "veridis.health_ping",
            "schedule": 3600.0,
        },
    },
)


@celery_app.task(name="veridis.health_ping")
def health_ping() -> dict[str, str]:
    return {"status": "ok"}
