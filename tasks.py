from celery_config import celery_app
from sqlalchemy.orm import Session
from database import SessionLocal
from crud.user import get_users_in_queue, send_message_to_user
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.process_customers_trace")
def process_customers_trace():
    logger.info("✅ Spouštím Celery úlohu: process_customers_trace")
    db: Session = SessionLocal()
    try:
        users = get_users_in_queue(db)
        logger.info(f"🔍 Nalezeno {len(users)} uživatelů ke zpracování.")
        
        for user in users:
            send_message_to_user(db, user)
    except Exception as e:
        logger.error(f"❌ Chyba při zpracování uživatelů: {str(e)}")
    finally:
        db.close()
