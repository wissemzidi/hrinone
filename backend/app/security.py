from datetime import datetime
from sqlalchemy.orm import Session
from . import models


def record_event(db: Session, event_type: str, *, user_id=None, email="", method="", path="", status_code=0, ip="unknown", user_agent="", details=""):
    db.add(models.SecurityEvent(
        user_id=user_id, email=(email or "")[:120], event_type=event_type[:60],
        method=method[:10], path=path[:240], status_code=status_code,
        ip_address=(ip or "unknown")[:64], user_agent=(user_agent or "")[:300],
        details=(details or "")[:300], occurred_at=datetime.utcnow(),
    ))
    db.commit()
