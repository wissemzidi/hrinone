import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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


@router.post("", status_code=201)
async def apply(
    job_id: int = Form(...),
    candidate_name: str = Form(..., min_length=1, max_length=120),
    candidate_email: str = Form(...),
    cover_note: str = Form("", max_length=1000),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Public: a candidate applies with a CV. The CV is summarised and scored for the admin."""
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
    data = await cv.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(422, "That file is larger than 5 MB")

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
