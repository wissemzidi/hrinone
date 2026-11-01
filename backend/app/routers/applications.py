import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import cv as cv_tools
from .. import models, schemas
from ..auth import admin_only
from ..database import get_db

router = APIRouter(prefix="/applications", tags=["applications"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
ALLOWED = {".pdf", ".docx", ".txt"}
MAX_BYTES = 5 * 1024 * 1024


def _validate_cv_payload(ext: str, data: bytes) -> None:
    """Reject extension-only spoofing before parsers receive untrusted bytes."""
    valid = False
    if ext == ".pdf":
        valid = data.startswith(b"%PDF-")
    elif ext == ".docx":
        try:
            with zipfile.ZipFile(BytesIO(data)) as archive:
                names = set(archive.namelist())
                valid = "[Content_Types].xml" in names and "word/document.xml" in names
        except (zipfile.BadZipFile, OSError):
            valid = False
    elif ext == ".txt":
        try:
            data.decode("utf-8-sig")
            valid = True
        except UnicodeDecodeError:
            valid = False
    if not valid:
        raise HTTPException(415, "The file content does not match a valid PDF, DOCX or UTF-8 TXT file")


@router.post("", status_code=201)
async def apply(
    request: Request,
    job_id: int = Form(...),
    candidate_name: str = Form(..., min_length=1, max_length=120),
    candidate_email: str = Form(...),
    cover_note: str = Form("", max_length=1000),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Public: a candidate applies with a CV. The CV is summarised and scored for the admin."""
    host = request.client.host if request and request.client else "unknown"
    limit(f"candidate-apply:{host}", 12, 3600)
    job = db.get(models.Job, job_id)
    if not job or job.status != "open":
        raise HTTPException(404, "This role is no longer open")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(candidate_email.strip()))
    except ValidationError:
        raise HTTPException(422, "Enter a valid email address")

    ext = Path(cv.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(422, "Upload your CV as a PDF, DOCX or TXT file")
    data = await cv.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(422, "That file is larger than 5 MB")

    _validate_cv_payload(ext, data)
    analysis = cv_tools.analyze(cv_tools.extract_text(ext, data), job.skills_list, job.min_years)

    UPLOAD_DIR.mkdir(exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / stored).write_bytes(data)

    application = models.Application(
        job_id=job.id,
        candidate_name=candidate_name.strip(),
        candidate_email=email,
        cover_note=cover_note.strip(),
        cv_filename=Path(cv.filename).name,
        cv_path=stored,
        score=analysis["score"],
        analysis=analysis,
    )
    db.add(application)
    db.commit()
    return {"id": application.id}


@router.post("/upload", status_code=201, dependencies=[Depends(admin_only)])
async def upload_candidate_cv(
    job_id: int = Form(...),
    candidate_name: str = Form(..., min_length=1, max_length=120),
    candidate_email: str = Form(...),
    cover_note: str = Form("", max_length=1000),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Admin-only: HR uploads a CV received outside the candidate portal."""
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(404, "Select a valid job role")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(candidate_email.strip()))
    except ValidationError:
        raise HTTPException(422, "Enter a valid email address")

    ext = Path(cv.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(422, "Upload the CV as a PDF, DOCX or TXT file")
    data = await cv.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(422, "That file is larger than 5 MB")

    _validate_cv_payload(ext, data)
    text = cv_tools.extract_text(ext, data)
    analysis = cv_tools.analyze(text, job.skills_list, job.min_years)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / stored
    path.write_bytes(data)
    try:
        application = models.Application(
            job_id=job.id,
            candidate_name=candidate_name.strip(),
            candidate_email=email,
            cover_note=cover_note.strip(),
            cv_filename=Path(cv.filename or f"candidate{ext}").name[:200],
            cv_path=stored,
            score=analysis["score"],
            analysis=analysis,
        )
        db.add(application)
        db.commit()
        db.refresh(application)
        return {"id": application.id, "score": application.score, "analysis": analysis}
    except Exception:
        path.unlink(missing_ok=True)
        db.rollback()
        raise


@router.get("", response_model=list[schemas.ApplicationOut], dependencies=[Depends(admin_only)])
def list_applications(job_id: int | None = None, status: str | None = None, db: Session = Depends(get_db)):
    q = select(models.Application).options(joinedload(models.Application.job))
    if job_id:
        q = q.where(models.Application.job_id == job_id)
    if status:
        q = q.where(models.Application.status == status)
    return db.scalars(q.order_by(models.Application.score.desc(), models.Application.created_at.desc())).all()


def _get(db: Session, app_id: int) -> models.Application:
    app = db.get(models.Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app


@router.patch("/{app_id}", response_model=schemas.ApplicationOut, dependencies=[Depends(admin_only)])
def set_status(app_id: int, data: schemas.ApplicationStatus, db: Session = Depends(get_db)):
    app = _get(db, app_id)
    app.status = data.status
    db.commit()
    db.refresh(app)
    return app


@router.get("/{app_id}/cv", dependencies=[Depends(admin_only)])
def download_cv(app_id: int, db: Session = Depends(get_db)):
    app = _get(db, app_id)
    path = UPLOAD_DIR / app.cv_path
    if not path.exists():
        raise HTTPException(404, "The CV file is missing from the server")
    return FileResponse(path, filename=app.cv_filename)


@router.delete("/{app_id}", status_code=204, dependencies=[Depends(admin_only)])
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = _get(db, app_id)
    (UPLOAD_DIR / app.cv_path).unlink(missing_ok=True)
    db.delete(app)
    db.commit()
