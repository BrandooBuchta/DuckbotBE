from celery_config import celery_app
from sqlalchemy.orm import Session
from crud.user import get_users_in_queue, send_message_to_user
from database import SessionLocal
from celery.schedules import crontab
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.process_customers_trace")
def process_customers_trace():
    logger.info("Spouštím Celery úlohu: process_customers_trace")
    db: Session = SessionLocal()
    try:
        users = get_users_in_queue(db)
        logger.info(f"Nalezeno {len(users)} uživatelů ke zpracování.")
        
        for user in users:
            send_message_to_user(db, user)
    except Exception as e:
        logger.error(f"Chyba při zpracování uživatelů: {str(e)}")
    finally:
        db.close()

celery_app.conf.beat_schedule = {
    "run-process_customers_trace-every-minute": {
        "task": "tasks.process_customers_trace",
        "schedule": crontab(minute="*/1"),  # Spustí se každých 5 minut
    },
}
