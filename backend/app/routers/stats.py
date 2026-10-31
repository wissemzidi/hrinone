from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..auth import admin_only
from ..database import get_db

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(admin_only)])


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    today = date.today()
    Leave = models.LeaveRequest

    def leaves(*conditions):
        q = select(Leave).options(joinedload(Leave.employee)).where(*conditions)
        return [schemas.LeaveOut.model_validate(x) for x in db.scalars(q.order_by(Leave.start_date)).all()]

    by_dept = db.execute(
        select(models.Department.name, func.count(models.Employee.id))
        .select_from(models.Department)
        .outerjoin(
            models.Employee,
            (models.Employee.department_id == models.Department.id) & (models.Employee.status == "active"),
        )
        .group_by(models.Department.id)
        .order_by(func.count(models.Employee.id).desc())
    ).all()

    return {
        "total_employees": db.scalar(select(func.count(models.Employee.id))),
        "active_employees": db.scalar(
            select(func.count(models.Employee.id)).where(models.Employee.status == "active")
        ),
        "out_today": leaves(Leave.status == "approved", Leave.start_date <= today, Leave.end_date >= today),
        "pending": leaves(Leave.status == "pending"),
        "by_department": [{"name": n, "count": c} for n, c in by_dept],
    }
