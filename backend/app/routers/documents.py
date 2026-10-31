from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import models
from ..auth import admin_only, current_user, employee_only
from ..database import get_db
from ..docgen import DOC_TYPES, build_docx
from ..notify import notify_admins, notify_employee

router = APIRouter(prefix="/documents", tags=["documents"])


class RequestIn(BaseModel):
    doc_type: Literal["work_certificate", "leave_summary", "training_record", "salary_certificate"]
    purpose: str = Field(default="", max_length=200)


class DecisionIn(BaseModel):
    status: Literal["approved", "rejected"]
    salary: str = Field(default="", max_length=100)  # required to approve a salary certificate
    note: str = Field(default="", max_length=300)


def out(r: models.DocumentRequest) -> dict:
    return {
        "id": r.id,
        "doc_type": r.doc_type,
        "label": DOC_TYPES[r.doc_type]["label"],
        "purpose": r.purpose,
        "status": r.status,
        "note": r.note,
        "created_at": r.created_at,
        "employee": {"id": r.employee.id, "first_name": r.employee.first_name,
                     "last_name": r.employee.last_name, "job_title": r.employee.job_title},
    }


def create_request(db: Session, employee: models.Employee, doc_type: str, purpose: str = "") -> models.DocumentRequest:
    """Shared by the form and the chat assistant. Low-risk documents are ready at once; others wait for HR."""
    auto = DOC_TYPES[doc_type]["auto"]
    req = models.DocumentRequest(employee_id=employee.id, doc_type=doc_type, purpose=purpose.strip(),
                                 status="ready" if auto else "pending")
    db.add(req)
    db.flush()
    if not auto:
        notify_admins(db, "Document to approve",
                      f"{employee.first_name} {employee.last_name} asked for a {DOC_TYPES[doc_type]['label'].lower()}.",
                      "document")
    db.commit()
    db.refresh(req)
    return req


@router.post("", status_code=201)
def request_document(data: RequestIn, db: Session = Depends(get_db), user: models.User = Depends(employee_only)):
    return out(create_request(db, user.employee, data.doc_type, data.purpose))


@router.get("/mine")
def my_documents(db: Session = Depends(get_db), user: models.User = Depends(employee_only)):
    q = select(models.DocumentRequest).options(joinedload(models.DocumentRequest.employee)).where(
        models.DocumentRequest.employee_id == user.employee_id).order_by(models.DocumentRequest.created_at.desc())
    return [out(r) for r in db.scalars(q).all()]


@router.get("", dependencies=[Depends(admin_only)])
def all_documents(status: str | None = None, db: Session = Depends(get_db)):
    q = select(models.DocumentRequest).options(joinedload(models.DocumentRequest.employee))
    if status:
        q = q.where(models.DocumentRequest.status == status)
    return [out(r) for r in db.scalars(q.order_by(models.DocumentRequest.created_at.desc()).limit(200)).all()]


@router.patch("/{req_id}", dependencies=[Depends(admin_only)])
def decide(req_id: int, data: DecisionIn, db: Session = Depends(get_db)):
    """HR approves or rejects a document that is not issued automatically."""
    req = db.get(models.DocumentRequest, req_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if req.status != "pending":
        raise HTTPException(409, "This request was already decided")
    if data.status == "approved":
        if req.doc_type == "salary_certificate":
            if not data.salary.strip():
                raise HTTPException(422, "Enter the salary to print on the certificate")
            req.details = {"salary": data.salary.strip()}
        req.status = "ready"
        notify_employee(db, req.employee, "Your document is ready",
                        f"Your {DOC_TYPES[req.doc_type]['label'].lower()} was approved. Download it from the Assistant page.",
                        "document")
    else:
        req.status = "rejected"
        req.note = data.note.strip()
        notify_employee(db, req.employee, "Document request declined",
                        data.note.strip() or f"Your {DOC_TYPES[req.doc_type]['label'].lower()} request was declined.",
                        "document")
    db.commit()
    db.refresh(req)
    return out(req)


@router.get("/{req_id}/download")
def download(req_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    req = db.get(models.DocumentRequest, req_id, options=[
        joinedload(models.DocumentRequest.employee).joinedload(models.Employee.department),
        joinedload(models.DocumentRequest.employee).selectinload(models.Employee.leaves),
        joinedload(models.DocumentRequest.employee).selectinload(models.Employee.trainings).joinedload(models.TrainingAssignment.course),
    ])
    if not req or (user.role != "admin" and req.employee_id != user.employee_id):
        raise HTTPException(404, "Document not found")  # same answer for "not yours" so ids can't be probed
    if req.status != "ready":
        raise HTTPException(409, "This document isn't ready yet")
    data = build_docx(req, date.today())
    filename = f"{req.doc_type}-{req.employee.last_name.lower()}.docx".replace(" ", "-")
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
