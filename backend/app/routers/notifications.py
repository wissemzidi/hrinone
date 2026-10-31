from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .. import models
from ..auth import current_user
from ..database import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def mine(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    N = models.Notification
    items = db.scalars(select(N).where(N.user_id == user.id).order_by(N.created_at.desc(), N.id.desc()).limit(30)).all()
    unread = db.scalar(select(func.count(N.id)).where(N.user_id == user.id, N.is_read.is_(False)))
    return {
        "unread": unread,
        "items": [{"id": n.id, "title": n.title, "body": n.body, "kind": n.kind,
                   "is_read": n.is_read, "created_at": n.created_at} for n in items],
    }


@router.post("/read-all", status_code=204)
def read_all(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    db.execute(update(models.Notification).where(models.Notification.user_id == user.id).values(is_read=True))
    db.commit()
