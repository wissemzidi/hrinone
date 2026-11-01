
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from . import models
from .database import get_db


# --------------------------------------------------
# Configuration
# --------------------------------------------------

APP_ENV = os.getenv("HRINONE_ENV", "development").strip().lower()

TOKEN_HOURS = int(os.getenv("HRINONE_TOKEN_HOURS", "4"))

if not 1 <= TOKEN_HOURS <= 24:
    raise RuntimeError("HRINONE_TOKEN_HOURS must be between 1 and 24")

SESSION_COOKIE = "hrinone_session"
CSRF_COOKIE = "hrinone_csrf"

COOKIE_SECURE = (
    APP_ENV == "production"
    or os.getenv("HRINONE_COOKIE_SECURE", "false").strip().lower() == "true"
)

COOKIE_SAMESITE = os.getenv(
    "HRINONE_COOKIE_SAMESITE",
    "none" if COOKIE_SECURE else "lax",
).strip().lower()

if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    raise RuntimeError(
        "HRINONE_COOKIE_SAMESITE must be lax, strict, or none"
    )

if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
    raise RuntimeError(
        "SameSite=None requires Secure cookies. "
        "Enable production mode or HRINONE_COOKIE_SECURE=true."
    )


# --------------------------------------------------
# Token helpers
# --------------------------------------------------

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --------------------------------------------------
# Session creation
# --------------------------------------------------

def create_session(user, request: Request, db: Session):
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)

    expires = datetime.utcnow() + timedelta(hours=TOKEN_HOURS)

    session = models.AuthSession(
        user_id=user.id,
        token_hash=_digest(token),
        csrf_hash=_digest(csrf),
        expires_at=expires,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "")[:500],
    )

    db.add(session)
    db.commit()

    return token, csrf, expires


# --------------------------------------------------
# Session revocation
# --------------------------------------------------

def revoke_session(token: str | None, db: Session):
    if not token:
        return

    token_hash = _digest(token)

    session = (
        db.query(models.AuthSession)
        .filter(
            models.AuthSession.token_hash == token_hash,
            models.AuthSession.revoked_at.is_(None),
        )
        .first()
    )

    if session:
        session.revoked_at = datetime.utcnow()
        db.commit()


# --------------------------------------------------
# Password verification
# --------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        310000,
    )

    return f"{salt.hex()}${hashed.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split("$", 1)

        salt = bytes.fromhex(salt_hex)

        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            310000,
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, TypeError, AttributeError):
        return False


# --------------------------------------------------
# Current authenticated user
# --------------------------------------------------

def current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(SESSION_COOKIE)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Please sign in",
        )

    token_hash = _digest(token)

    session = (
        db.query(models.AuthSession)
        .filter(
            models.AuthSession.token_hash == token_hash,
            models.AuthSession.revoked_at.is_(None),
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid session. Please sign in again.",
        )

    if session.expires_at <= datetime.utcnow():
        session.revoked_at = datetime.utcnow()
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="Session expired. Please sign in again.",
        )

    user = db.get(models.User, session.user_id)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists",
        )

    session.last_seen_at = datetime.utcnow()
    db.commit()

    return user


# --------------------------------------------------
# Role-based access
# --------------------------------------------------

def admin_only(user=Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return user


def employee_only(user=Depends(current_user)):
    if user.role != "employee":
        raise HTTPException(
            status_code=403,
            detail="Employee access required",
        )

    return user
