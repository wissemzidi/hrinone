from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..auth import admin_only, current_user
from ..database import get_db

router = APIRouter(prefix="/leaves", tags=["leaves"])


@router.get("", response_model=list[schemas.LeaveOut])
def list_leaves(
    status: str | None = None,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    q = select(models.LeaveRequest).options(joinedload(models.LeaveRequest.employee))
    if user.role != "admin":
        q = q.where(models.LeaveRequest.employee_id == user.employee_id)  # employees see only their own
    elif employee_id:
        q = q.where(models.LeaveRequest.employee_id == employee_id)
    if status:
        q = q.where(models.LeaveRequest.status == status)
    return db.scalars(q.order_by(models.LeaveRequest.start_date.desc())).all()


@router.post("", response_model=schemas.LeaveOut, status_code=201)
def create_leave(data: schemas.LeaveIn, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    emp_id = data.employee_id if user.role == "admin" else user.employee_id
    if emp_id is None or not db.get(models.Employee, emp_id):
        raise HTTPException(422, "Choose who this request is for")
    leave = models.LeaveRequest(employee_id=emp_id, **data.model_dump(exclude={"employee_id"}))
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@router.patch("/{leave_id}", response_model=schemas.LeaveOut, dependencies=[Depends(admin_only)])
def decide_leave(leave_id: int, data: schemas.LeaveDecision, db: Session = Depends(get_db)):
    leave = db.get(models.LeaveRequest, leave_id)
    if not leave:
        raise HTTPException(404, "Leave request not found")
    leave.status = data.status
    db.commit()
    db.refresh(leave)
    return leave


@router.delete("/{leave_id}", status_code=204)
def delete_leave(leave_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    leave = db.get(models.LeaveRequest, leave_id)
    if not leave:
        raise HTTPException(404, "Leave request not found")
    if user.role != "admin" and (leave.employee_id != user.employee_id or leave.status != "pending"):
        raise HTTPException(403, "You can only cancel your own pending requests")
    db.delete(leave)
    db.commit()
