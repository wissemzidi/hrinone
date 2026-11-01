from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import (create_session, current_user, verify_password, SESSION_COOKIE,
                    CSRF_COOKIE, COOKIE_SECURE, TOKEN_HOURS, revoke_session)
from ..database import get_db
from ..ratelimit import limit
from ..security import record_event

router = APIRouter(prefix="/auth", tags=["auth"])


def _client(request: Request):
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=schemas.LoginOut)
def login(data: schemas.LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    host = _client(request)
    email = data.email.strip().lower()[:120]
    try:
        limit(f"login:{host}", 15, 300)
        limit(f"login-user:{email}", 8, 300)
    except HTTPException as exc:
        if exc.status_code == 429:
            record_event(db, "login_rate_limited", email=email, method="POST", path="/api/auth/login",
                         status_code=429, ip=host, user_agent=request.headers.get("user-agent", ""),
                         details="Login throttling threshold reached")
        raise
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user or not verify_password(data.password, user.password_hash):
        record_event(db, "login_failed", email=email, method="POST", path="/api/auth/login", status_code=401,
                     ip=host, user_agent=request.headers.get("user-agent", ""), details="Invalid credentials")
        raise HTTPException(401, "Wrong email or password")
    if user.employee and user.employee.status != "active":
        record_event(db, "login_blocked", user_id=user.id, email=email, method="POST", path="/api/auth/login",
                     status_code=403, ip=host, user_agent=request.headers.get("user-agent", ""), details="Inactive account")
        raise HTTPException(403, "This account is inactive. Contact HR")
    token, csrf, expires = create_session(user, request, db)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=COOKIE_SECURE,
                        samesite="lax", max_age=TOKEN_HOURS * 3600, path="/")
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=COOKIE_SECURE,
                        samesite="lax", max_age=TOKEN_HOURS * 3600, path="/")
    record_event(db, "login_success", user_id=user.id, email=email, method="POST", path="/api/auth/login",
                 status_code=200, ip=host, user_agent=request.headers.get("user-agent", ""))
    return {"user": user}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    revoke_session(request.cookies.get(SESSION_COOKIE), db)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=COOKIE_SECURE, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=COOKIE_SECURE, samesite="lax")
    return {"ok": True}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return user


@router.get("/security/events")
def security_events(limit_count: int = 100, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Only admins can view security events")
    limit_count = max(1, min(limit_count, 500))
    rows = db.query(models.SecurityEvent).order_by(desc(models.SecurityEvent.occurred_at)).limit(limit_count).all()
    return [{"id": x.id, "occurred_at": x.occurred_at.isoformat() + "Z", "user_id": x.user_id,
             "email": x.email, "event_type": x.event_type, "method": x.method, "path": x.path,
             "status_code": x.status_code, "ip_address": x.ip_address, "user_agent": x.user_agent,
             "details": x.details} for x in rows]


@router.get("/security/sessions")
def security_sessions(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Only admins can view sessions")
    rows = db.query(models.AuthSession).filter(models.AuthSession.revoked_at.is_(None),
            models.AuthSession.expires_at > datetime.utcnow()).order_by(desc(models.AuthSession.last_seen_at)).limit(300).all()
    return [{"id": x.id, "user_id": x.user_id, "email": db.get(models.User, x.user_id).email if db.get(models.User, x.user_id) else "deleted",
             "created_at": x.created_at.isoformat() + "Z", "last_seen_at": x.last_seen_at.isoformat() + "Z",
             "expires_at": x.expires_at.isoformat() + "Z", "ip_address": x.ip_address, "user_agent": x.user_agent}
            for x in rows]


@router.delete("/security/sessions/{session_id}")
def revoke_admin_session(session_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Only admins can revoke sessions")
    session = db.get(models.AuthSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    session.revoked_at = datetime.utcnow()
    db.commit()
    record_event(db, "session_revoked_by_admin", user_id=user.id, email=user.email,
                 method="DELETE", path=f"/api/auth/security/sessions/{session_id}", status_code=200)
    return {"ok": True}
