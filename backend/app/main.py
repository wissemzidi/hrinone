from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
import hashlib, hmac, os
from . import config  # Load backend/.env before importing security settings
from .auth import SESSION_COOKIE
from .security import record_event
from . import llm, models  # noqa: F401
from .database import Base, SessionLocal, engine
from .routers import (analytics, applications, assistant, auth, departments, documents, employees,
                      jobs, leaves, notifications, stats, training, doc_intelligence)
from .seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="hrinone API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in __import__("os").getenv(
        "HRINONE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,https://hrinone.netlify.app"
    ).split(",") if origin.strip()],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    allow_credentials=True,
)

for r in (auth.router, departments.router, employees.router, leaves.router,
          stats.router, jobs.router, applications.router, analytics.router, training.router,
          notifications.router, documents.router, assistant.router, doc_intelligence.router):
    app.include_router(r, prefix="/api")


@app.middleware("http")
async def security_headers_and_audit(request: Request, call_next):
    unsafe = request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
    sensitive_read = request.method.upper() == "GET" and any(
        marker in request.url.path for marker in ("/applications", "/employees", "/documents", "/doc-intelligence", "/security/")
    )
    session_token = request.cookies.get(SESSION_COOKIE)
    # Login is exempt: it has no session to protect, and a stale session cookie left in the browser
    # (expired, revoked or from a re-created database) must not lock the user out of signing in again.
    if unsafe and session_token and request.url.path != "/api/auth/login":
        cookie_csrf = request.cookies.get("hrinone_csrf", "")
        header_csrf = request.headers.get("x-csrf-token", "")
        valid_pair = bool(cookie_csrf and header_csrf and hmac.compare_digest(cookie_csrf, header_csrf))
        if valid_pair:
            try:
                from .database import SessionLocal
                from . import models
                token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
                with SessionLocal() as csrf_db:
                    stored = csrf_db.query(models.AuthSession.csrf_hash).filter_by(token_hash=token_hash).scalar()
                    valid_pair = bool(stored and hmac.compare_digest(stored, hashlib.sha256(cookie_csrf.encode("utf-8")).hexdigest()))
            except Exception:
                valid_pair = False
        if not valid_pair:
            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed. Refresh the page and try again."})
    response = await call_next(request)
    # Log authenticated mutations without storing request bodies, passwords, tokens or query strings.
    if ((unsafe or sensitive_read) and session_token and request.url.path.startswith("/api/")
            and request.url.path != "/api/auth/login" and not request.url.path.startswith("/api/auth/security/")):
        try:
            from .database import SessionLocal
            from . import models
            token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
            with SessionLocal() as audit_db:
                session = audit_db.query(models.AuthSession).filter_by(token_hash=token_hash).first()
                record_event(audit_db, "api_mutation" if unsafe else "sensitive_data_access", user_id=session.user_id if session else None,
                    method=request.method, path=request.url.path, status_code=response.status_code,
                    ip=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("user-agent", ""),
                    details="Authenticated write request" if unsafe else "Sensitive API read")
        except Exception:
            # Audit failures must be visible in server logs; do not expose internals to clients.
            import logging
            logging.exception("Failed to persist security audit event")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    if request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-store")
    if __import__("os").getenv("HRINONE_ENV", "development").lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.head("/")
@app.get("/")
@app.get("/api/health")
def health():
    return {"status": "ok", "ai": llm.provider()}
