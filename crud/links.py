from sqlalchemy.orm import Session
from models.bot import BotList
from schemas.links import CreateLink, ReadLink, UpdateLink
import uuid
from uuid import UUID


def get_link(db: Session, link_id: UUID):
    db_link = db.query(BotList).filter(BotList.is_faq == False, BotList.id == link_id).first()
    if not db_link:
        return None, 404

    link = ReadLink(
        id=db_link.id,
        bot_id=db_link.bot_id,
        position=db_link.position,
        share=db_link.share,
        currently_assigned=db_link.currently_assigned,
        parent=db_link.parent,
        child=db_link.child,
    )
    return link, 200


def get_base_link(db: Session, link_id: UUID):
    db_link = db.query(BotList).filter(BotList.is_faq == False, BotList.id == link_id).first()
    if not db_link:
        return None, 404

    return db_link, 200


def get_all_links(db: Session, bot_id: UUID):
    db_links = db.query(BotList).filter(BotList.is_faq == False, BotList.bot_id == bot_id).all()

    if not db_links:
        return [], 404

    links = []
    for l in db_links:
        links.append(ReadLink(
            id=l.id,
            bot_id=bot_id,
            position=l.position,
            share=l.share,
            currently_assigned=l.currently_assigned,
            parent=l.parent,
            child=l.child,
        ))

    return links, 200


def update_link(db: Session, link_id: UUID, link: UpdateLink):
    db_link, status = get_base_link(db, link_id)
    if not db_link:
        return 404, None
    for key, value in link.dict(exclude_unset=True).items():
        setattr(db_link, key, value)
    db.commit()
    db.refresh(db_link)
    return db_link, 200


def create_link(db: Session, bot_id: UUID):
    db_links, status = get_all_links(db, bot_id)

    db_link = BotList(
        id=uuid.uuid4(),
        bot_id=bot_id,
        is_faq=False,
        currently_assigned=0,
        share=0,
        parent=f"Link Alias {len(db_links) + 1}",
        child=f"Link URL {len(db_links) + 1}",
        position=len(db_links) + 1
    )

    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return 200


def delete_link(db: Session, link_id: UUID):
    db_link, status = get_base_link(db, link_id)
    if db_link:
        db.delete(db_link)
        db.commit()
        return 200, True
    return 404, False

