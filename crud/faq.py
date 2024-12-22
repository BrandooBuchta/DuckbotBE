from sqlalchemy.orm import Session
from models.bot import BotList
from schemas.faq import CreateFAQ, ReadFAQ, UpdateFAQ
import uuid
from uuid import UUID


def get_faq(db: Session, faq_id: UUID):
    db_faq = db.query(BotList).filter(BotList.is_faq == True, BotList.id == faq_id).first()
    if not db_faq:
        return None, 404

    faq = ReadFAQ(
        id=db_faq.id,
        bot_id=db_faq.bot_id,
        position=db_faq.position,
        parent=db_faq.parent,
        child=db_faq.child,
    )
    return faq, 200


def get_base_faq(db: Session, faq_id: UUID):
    db_faq = db.query(BotList).filter(BotList.is_faq == True, BotList.id == faq_id).first()
    if not db_faq:
        return None, 404

    return db_faq, 200


def get_all_faqs(db: Session, bot_id: UUID):
    db_faqs = db.query(BotList).filter(BotList.is_faq == True, BotList.bot_id == bot_id).all()

    if not db_faqs:
        return [], 404

    faqs = []
    for l in db_faqs:
        faqs.append(ReadFAQ(
            id=l.id,
            bot_id=bot_id,
            position=l.position,
            parent=l.parent,
            child=l.child,
        ))

    return faqs, 200

def get_all_formated_faqs(db: Session, bot_id: UUID):
    db_faqs = db.query(BotList).filter(BotList.is_faq == True, BotList.bot_id == bot_id).all()

    if not db_faqs:
        return "", 404

    formatted_faqs = ""
    for faq in db_faqs:
        formatted_faqs += f"*{faq.parent}*\n{faq.child}\n\n"

    return formatted_faqs.strip(), 200


def update_faq(db: Session, faq_id: UUID, faq: UpdateFAQ):
    db_faq, status = get_base_faq(db, faq_id)
    if not db_faq:
        return 404, None
    for key, value in faq.dict(exclude_unset=True).items():
        setattr(db_faq, key, value)
    db.commit()
    db.refresh(db_faq)
    return db_faq, 200


def create_faq(db: Session, bot_id: UUID):
    db_faqs, status = get_all_faqs(db, bot_id)

    db_faq = BotList(
        id=uuid.uuid4(),
        bot_id=bot_id,
        is_faq=True,
        parent=f"Otázka {len(db_faqs) + 1}",
        child=f"Odpověď {len(db_faqs) + 1}",
        position=len(db_faqs) + 1
    )

    db.add(db_faq)
    db.commit()
    db.refresh(db_faq)
    return 200


def delete_faq(db: Session, faq_id: UUID):
    db_faq, status = get_base_faq(db, faq_id)
    if db_faq:
        db.delete(db_faq)
        db.commit()
        return 200, True
    return 404, False
