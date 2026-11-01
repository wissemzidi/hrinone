import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi import Request
from sqlalchemy.orm import Session

from . import models
from .database import get_db

APP_ENV = os.getenv("HRINONE_ENV", "development").strip().lower()
TOKEN_HOURS = int(os.getenv("HRINONE_TOKEN_HOURS", "4"))
if not 1 <= TOKEN_HOURS <= 24:
    raise RuntimeError("HRINONE_TOKEN_HOURS must be between 1 and 24")
SESSION_COOKIE = "hrinone_session"
CSRF_COOKIE = "hrinone_csrf"
COOKIE_SECURE = APP_ENV == "production" or os.getenv("HRINONE_COOKIE_SECURE", "false").lower() == "true"

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_session(user: models.User, request: Request, db: Session) -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=TOKEN_HOURS)
    db.add(models.AuthSession(
        user_id=user.id, token_hash=_digest(token), csrf_hash=_digest(csrf), expires_at=expires,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "")[:300],
    ))
    db.commit()
    return token, csrf, expires

def revoke_session(token: str | None, db: Session) -> None:
    if not token:
        return
    session = db.query(models.AuthSession).filter_by(token_hash=_digest(token), revoked_at=None).first()
    if session:
        session.revoked_at = datetime.utcnow()
        db.commit()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
        if len(salt) != 32 or len(digest) != 64:
            return False
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
        return hmac.compare_digest(check, digest)
    except (ValueError, TypeError):
        return False


def current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "Please sign in")
    session = db.query(models.AuthSession).filter_by(token_hash=_digest(token), revoked_at=None).first()
    if not session or session.expires_at <= datetime.utcnow():
        raise HTTPException(401, "Your session has expired. Please sign in again")
    user = db.get(models.User, session.user_id)
    if not user:
        raise HTTPException(401, "Account no longer exists")
    session.last_seen_at = datetime.utcnow()
    db.commit()
    return user


def admin_only(user: models.User = Depends(current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(403, "Only admins can do this")
    return user


def employee_only(user: models.User = Depends(current_user)) -> models.User:
    if user.role != "employee" or user.employee_id is None:
        raise HTTPException(403, "This is for employees")
    return user
