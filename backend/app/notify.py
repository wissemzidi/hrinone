"""Create in-app notifications. Callers commit the session."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


def notify(db: Session, user_id: int | None, title: str, body: str = "", kind: str = "info") -> None:
    if user_id:
        db.add(models.Notification(user_id=user_id, title=title[:120], body=body[:400], kind=kind))


def notify_employee(db: Session, employee: models.Employee, title: str, body: str = "", kind: str = "info") -> None:
    if employee.user:
        notify(db, employee.user.id, title, body, kind)


def notify_admins(db: Session, title: str, body: str = "", kind: str = "info") -> None:
    for uid in db.scalars(select(models.User.id).where(models.User.role == "admin")).all():
        notify(db, uid, title, body, kind)
