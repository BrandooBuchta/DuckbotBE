from celery import Celery
from celery.schedules import crontab
import os

# Oprava REDIS_URL s vypnutým SSL certifikátem
REDIS_URL = os.getenv("REDIS_URL")

if REDIS_URL and REDIS_URL.startswith("rediss://"):
    REDIS_URL += "?ssl_cert_reqs=CERT_NONE"  # Přidání certifikátu do URL

if not REDIS_URL:
    raise ValueError("❌ REDIS_URL není nastaven! Přidej ho do Environment Variables.")

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"]  # Zahrne všechny Celery úlohy
)

celery_app.conf.update(
    task_routes={
        "tasks.process_customers_trace": {"queue": "default"},
    },
    task_serializer="json",
)

# ✅ Přidání Celery Beat plánování úloh
celery_app.conf.beat_schedule = {
    "run-process_customers_trace-every-minute": {
        "task": "tasks.process_customers_trace",
        "schedule": crontab(minute="*/1"),  # Spustí se každou minutu
    },
}
