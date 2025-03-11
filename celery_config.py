from celery import Celery
from celery.schedules import crontab
import os

# Správné připojení k Redis Upstash
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("❌ REDIS_URL není nastaven!")

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_routes={
        "app.tasks.process_customers_trace": {"queue": "default"},
    },
    task_serializer="json",
)

# ✅ Přidání Celery Beat plánování úloh
celery_app.conf.beat_schedule = {
    "run-process_customers_trace-every-minute": {
        "task": "app.tasks.process_customers_trace",
        "schedule": crontab(minute="*/1"),  # Spustí se každou minutu
    },
}
