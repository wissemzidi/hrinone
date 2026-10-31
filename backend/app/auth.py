import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db

# Set HRINONE_SECRET in the environment for anything beyond local development.
SECRET = os.getenv("HRINONE_SECRET", "dev-only-secret-change-me")
TOKEN_HOURS = 12
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return hmac.compare_digest(check, digest)


def create_token(user: models.User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, SECRET, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> models.User:
    if not creds:
        raise HTTPException(401, "Please sign in")
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Your session has expired. Please sign in again")
    user = db.get(models.User, int(payload["sub"]))
    if not user:
        raise HTTPException(401, "Account no longer exists")
    return user


def admin_only(user: models.User = Depends(current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(403, "Only admins can do this")
    return user
