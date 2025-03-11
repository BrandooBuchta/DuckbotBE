from celery import Celery
from celery.schedules import crontab
import os

REDIS_URL = os.getenv("REDIS_URL")

# Pokud používáme rediss:// (šifrované spojení na Redis), musíme přidat správný certifikát
if REDIS_URL and REDIS_URL.startswith("rediss://"):
    REDIS_URL += "?ssl_cert_reqs=CERT_NONE"  # ✅ Přidání správné SSL konfigurace

# Ověření, že REDIS_URL existuje
if not REDIS_URL:
    raise ValueError("❌ REDIS_URL není nastaven!")

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"]
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
