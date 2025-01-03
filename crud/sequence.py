# crud/sequences.py 

from sqlalchemy.orm import Session
from models.bot import Sequence
from schemas.bot import ReadSequence, UpdateSequence
import uuid
from uuid import UUID
from datetime import timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_sequence(db: Session, sequence_id: UUID):
    db_sequence = db.query(Sequence).filter(Sequence.id == sequence_id).first()
    if not db_sequence:
        return None, 404

    return db_sequence, 200

def get_all_sequences(db: Session, bot_id: UUID):
    db_sequences = db.query(Sequence).filter(Sequence.bot_id == bot_id).all()

    if not db_sequences:
        return [], 404

    return db_sequences, 200

def get_sequences(db: Session):
    db_sequences = db.query(Sequence).filter(Sequence.is_active == True).all()

    if not db_sequences:
        return [], 404

    return db_sequences, 200

def update_sequence(db: Session, sequence_id: UUID, update_data: UpdateSequence):
    db_sequence, status = get_sequence(db, sequence_id)
    if not db_sequence:
        return 404, None
    
    if not isinstance(update_data, dict):  # Convert Pydantic model to dict
        update_data = update_data.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_sequence, key, value)
    
    db.commit()
    db.refresh(db_sequence)
    return db_sequence, 200

def update_send_at(db: Session, sequence_id: UUID, interval: int):
    """
    Aktualizuje atribut `send_at` sekvence podle zadaného intervalu (v dnech).
    """
    db_sequence, status = get_sequence(db, sequence_id)
    if not db_sequence:
        logger.error(f"Sequence with ID {sequence_id} not found.")
        return None, 404

    if db_sequence.send_at:
        new_send_at = db_sequence.send_at + timedelta(days=interval)
        logger.debug(f"Attempting to update send_at for sequence {sequence_id}: Current: {db_sequence.send_at}, New: {new_send_at}")
        db_sequence.send_at = new_send_at
        db.commit()
        db.refresh(db_sequence)
        logger.debug(f"Updated send_at for sequence {sequence_id}: {db_sequence.send_at}")
        return db_sequence, 200
    else:
        logger.error(f"Sequence {sequence_id} has no valid `send_at` value.")
        return None, 400

def create_sequence(db: Session, bot_id: UUID):
    db_sequences, status = get_all_sequences(db, bot_id)

    db_sequence = Sequence(
        id=uuid.uuid4(),
        bot_id=bot_id,
        name=f"Sekvence {len(db_sequences) + 1}",
        position=len(db_sequences) + 1,
        message="",
        for_new_client=False,
        for_client=False,
        repeat=False,
        send_at=None,
        send_immediately=True,
        starts_at=None,
        is_active=False,
        interval=None
    )

    db.add(db_sequence)
    db.commit()
    db.refresh(db_sequence)
    return 200


def delete_sequence(db: Session, sequence_id: UUID):
    db_sequence, status = get_sequence(db, sequence_id)
    if db_sequence:
        db.delete(db_sequence)
        db.commit()
        return 200, True
    return 404, False
