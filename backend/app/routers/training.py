from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..auth import admin_only, employee_only
from ..calc import effective_status
from ..database import get_db
from ..notify import notify_employee

router = APIRouter(prefix="/training", tags=["training"])


class CourseIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    hours: float = Field(default=2, gt=0, le=200)
    mandatory: bool = False


class AssignIn(BaseModel):
    course_id: int
    employee_ids: list[int] = []
    department_id: int | None = None
    due_date: date


class StatusIn(BaseModel):
    status: Literal["assigned", "completed", "missed"]


class RemindIn(BaseModel):
    department_id: int | None = None


def _item(a: models.TrainingAssignment, today: date) -> dict:
    e = a.employee
    return {
        "id": a.id,
        "employee": {"id": e.id, "first_name": e.first_name, "last_name": e.last_name, "job_title": e.job_title},
        "department": e.department.name if e.department else None,
        "department_id": e.department_id,
        "course": {"id": a.course.id, "title": a.course.title, "hours": a.course.hours, "mandatory": a.course.mandatory},
        "status": a.status,
        "effective_status": effective_status(a.status, a.due_date, today),
        "due_date": a.due_date,
        "completed_at": a.completed_at,
        "last_reminded_at": a.last_reminded_at,
    }


def _load(db: Session):
    return select(models.TrainingAssignment).options(
        joinedload(models.TrainingAssignment.employee).joinedload(models.Employee.department),
        joinedload(models.TrainingAssignment.course),
    )


# ------------------------------------------------------------------ courses
@router.get("/courses", dependencies=[Depends(admin_only)])
def list_courses(db: Session = Depends(get_db)):
    out = []
    for c in db.scalars(select(models.Course).options(joinedload(models.Course.assignments)).order_by(models.Course.title)).unique():
        out.append({"id": c.id, "title": c.title, "description": c.description, "hours": c.hours,
                    "mandatory": c.mandatory, "assigned": len(c.assignments),
                    "completed": sum(1 for a in c.assignments if a.status == "completed")})
    return out


@router.post("/courses", status_code=201, dependencies=[Depends(admin_only)])
def create_course(data: CourseIn, db: Session = Depends(get_db)):
    c = models.Course(**data.model_dump())
    db.add(c)
    db.commit()
    return {"id": c.id}


@router.delete("/courses/{course_id}", status_code=204, dependencies=[Depends(admin_only)])
def delete_course(course_id: int, db: Session = Depends(get_db)):
    c = db.get(models.Course, course_id)
    if not c:
        raise HTTPException(404, "Course not found")
    db.delete(c)
    db.commit()


# ------------------------------------------------------------------ assignments (HR)
@router.get("/assignments", dependencies=[Depends(admin_only)])
def list_assignments(status: str | None = None, department_id: int | None = None,
                     employee_id: int | None = None, db: Session = Depends(get_db)):
    today = date.today()
    q = _load(db)
    if employee_id:
        q = q.where(models.TrainingAssignment.employee_id == employee_id)
    items = [_item(a, today) for a in db.scalars(q.order_by(models.TrainingAssignment.due_date)).unique()]
    if department_id:
        items = [i for i in items if i["department_id"] == department_id]
    if status:
        items = [i for i in items if i["effective_status"] == status]
    return items


@router.post("/assign", status_code=201, dependencies=[Depends(admin_only)])
def assign(data: AssignIn, db: Session = Depends(get_db)):
    """HR programs a training for people or a whole department. Each person gets a notification."""
    course = db.get(models.Course, data.course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    q = select(models.Employee).options(joinedload(models.Employee.user)).where(models.Employee.status == "active")
    if data.department_id:
        q = q.where(models.Employee.department_id == data.department_id)
    elif data.employee_ids:
        q = q.where(models.Employee.id.in_(data.employee_ids))
    else:
        raise HTTPException(422, "Choose a department or at least one person")
    existing = set(db.scalars(select(models.TrainingAssignment.employee_id).where(
        models.TrainingAssignment.course_id == course.id, models.TrainingAssignment.status != "completed")))
    created = skipped = 0
    for emp in db.scalars(q).unique():
        if emp.id in existing:
            skipped += 1
            continue
        db.add(models.TrainingAssignment(employee_id=emp.id, course_id=course.id, due_date=data.due_date))
        notify_employee(db, emp, "New training assigned",
                        f"“{course.title}” ({course.hours:g} h), due {data.due_date.strftime('%d %b %Y')}.", "training")
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped}


@router.patch("/assignments/{a_id}", dependencies=[Depends(admin_only)])
def set_status(a_id: int, data: StatusIn, db: Session = Depends(get_db)):
    a = db.get(models.TrainingAssignment, a_id, options=[
        joinedload(models.TrainingAssignment.employee).joinedload(models.Employee.user),
        joinedload(models.TrainingAssignment.course)])
    if not a:
        raise HTTPException(404, "Assignment not found")
    a.status = data.status
    a.completed_at = date.today() if data.status == "completed" else None
    if data.status == "missed":
        notify_employee(db, a.employee, "You missed a training",
                        f"“{a.course.title}” was marked as missed. Contact HR to reschedule it.", "training")
    elif data.status == "completed":
        notify_employee(db, a.employee, "Training completed", f"“{a.course.title}” is recorded as completed. Well done!", "training")
    db.commit()
    return {"ok": True}


@router.delete("/assignments/{a_id}", status_code=204, dependencies=[Depends(admin_only)])
def delete_assignment(a_id: int, db: Session = Depends(get_db)):
    a = db.get(models.TrainingAssignment, a_id)
    if not a:
        raise HTTPException(404, "Assignment not found")
    db.delete(a)
    db.commit()


@router.post("/remind", dependencies=[Depends(admin_only)])
def remind(data: RemindIn, db: Session = Depends(get_db)):
    """HR sends a reminder to everyone who is overdue or missed a session (max once a day each)."""
    today = date.today()
    sent = 0
    for a in db.scalars(_load(db).options(joinedload(models.TrainingAssignment.employee).joinedload(models.Employee.user))).unique():
        if data.department_id and a.employee.department_id != data.department_id:
            continue
        if effective_status(a.status, a.due_date, today) not in ("overdue", "missed") or a.last_reminded_at == today:
            continue
        notify_employee(db, a.employee, "Training reminder",
                        f"“{a.course.title}” is still to do (was due {a.due_date.strftime('%d %b %Y')}). Please book your slot with HR.",
                        "training")
        a.last_reminded_at = today
        sent += 1
    db.commit()
    return {"reminded": sent}


@router.get("/overview", dependencies=[Depends(admin_only)])
def overview(db: Session = Depends(get_db)):
    today = date.today()
    per: dict[int, dict] = {}
    totals = {"assigned": 0, "completed": 0, "overdue": 0, "missed": 0}
    for a in db.scalars(select(models.TrainingAssignment)):
        s = effective_status(a.status, a.due_date, today)
        p = per.setdefault(a.employee_id, {"employee_id": a.employee_id, "total": 0, "completed": 0, "outstanding": 0, "hours_done": 0.0})
        p["total"] += 1
        totals["assigned"] += 1
        if s == "completed":
            p["completed"] += 1
            totals["completed"] += 1
            p["hours_done"] += a.course.hours
        elif s in ("overdue", "missed"):
            p["outstanding"] += 1
            totals[s] += 1
    return {"totals": totals, "people": list(per.values())}


# ------------------------------------------------------------------ employee view
@router.get("/mine")
def mine(db: Session = Depends(get_db), user: models.User = Depends(employee_only)):
    today = date.today()
    q = _load(db).where(models.TrainingAssignment.employee_id == user.employee_id).order_by(models.TrainingAssignment.due_date)
    items = [_item(a, today) for a in db.scalars(q).unique()]
    done = [i for i in items if i["effective_status"] == "completed"]
    return {
        "summary": {
            "total": len(items),
            "completed": len(done),
            "outstanding": sum(1 for i in items if i["effective_status"] in ("overdue", "missed")),
            "upcoming": sum(1 for i in items if i["effective_status"] == "assigned"),
            "hours_done": sum(i["course"]["hours"] for i in done),
        },
        "items": items,
    }
