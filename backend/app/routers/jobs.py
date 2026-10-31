from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import admin_only
from ..database import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _apply(job: models.Job, data: schemas.JobIn):
    values = data.model_dump()
    values["required_skills"] = ",".join(s.strip() for s in data.required_skills if s.strip())
    for k, v in values.items():
        setattr(job, k, v)


@router.get("", response_model=list[schemas.JobOut])
def open_jobs(db: Session = Depends(get_db)):
    """Public: roles candidates can apply to."""
    return db.scalars(select(models.Job).where(models.Job.status == "open").order_by(models.Job.title)).all()


@router.get("/manage", response_model=list[schemas.JobAdminOut], dependencies=[Depends(admin_only)])
def all_jobs(db: Session = Depends(get_db)):
    return db.scalars(select(models.Job).order_by(models.Job.status.desc(), models.Job.title)).all()


@router.post("", response_model=schemas.JobAdminOut, status_code=201, dependencies=[Depends(admin_only)])
def create_job(data: schemas.JobIn, db: Session = Depends(get_db)):
    job = models.Job()
    _apply(job, data)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.put("/{job_id}", response_model=schemas.JobAdminOut, dependencies=[Depends(admin_only)])
def update_job(job_id: int, data: schemas.JobIn, db: Session = Depends(get_db)):
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(404, "Role not found")
    _apply(job, data)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204, dependencies=[Depends(admin_only)])
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(404, "Role not found")
    db.delete(job)
    db.commit()
