from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, llm, models  # noqa: F401  (config loads backend/.env; models registers tables)
from .database import Base, SessionLocal, engine
from .routers import (analytics, applications, assistant, auth, departments, documents, employees,
                      jobs, leaves, notifications, stats, training)
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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, departments.router, employees.router, leaves.router,
          stats.router, jobs.router, applications.router, analytics.router, training.router,
          notifications.router, documents.router, assistant.router):
    app.include_router(r, prefix="/api")


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-store")  # API answers hold personal data
    return response


@app.get("/api/health")
def health():
    return {"status": "ok", "ai": llm.provider()}
