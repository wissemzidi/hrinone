from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..auth import admin_only, hash_password
from ..database import get_db

router = APIRouter(prefix="/employees", tags=["employees"], dependencies=[Depends(admin_only)])


def _get_or_404(db: Session, emp_id: int) -> models.Employee:
    emp = db.get(models.Employee, emp_id, options=[joinedload(models.Employee.department)])
    if not emp:
        raise HTTPException(404, "Employee not found")
    return emp


def _check_department(db: Session, dept_id: int | None):
    if dept_id is not None and not db.get(models.Department, dept_id):
        raise HTTPException(422, "Department does not exist")


@router.get("", response_model=list[schemas.EmployeeOut])
def list_employees(
    search: str | None = None,
    department_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = select(models.Employee).options(joinedload(models.Employee.department))
    if search:
        like = f"%{search}%"
        q = q.where(
            or_(
                models.Employee.first_name.ilike(like),
                models.Employee.last_name.ilike(like),
                models.Employee.email.ilike(like),
                models.Employee.job_title.ilike(like),
            )
        )
    if department_id:
        q = q.where(models.Employee.department_id == department_id)
    if status:
        q = q.where(models.Employee.status == status)
    return db.scalars(q.order_by(models.Employee.last_name, models.Employee.first_name)).all()


@router.get("/{emp_id}", response_model=schemas.EmployeeOut)
def get_employee(emp_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, emp_id)


@router.post("", response_model=schemas.EmployeeOut, status_code=201)
def create_employee(data: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    _check_department(db, data.department_id)
    values = data.model_dump()
    password = values.pop("password")
    emp = models.Employee(**values)
    emp.user = models.User(email=emp.email.lower(), password_hash=hash_password(password), role="employee")
    db.add(emp)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An employee with that email already exists")
    return _get_or_404(db, emp.id)


@router.put("/{emp_id}", response_model=schemas.EmployeeOut)
def update_employee(emp_id: int, data: schemas.EmployeeIn, db: Session = Depends(get_db)):
    emp = _get_or_404(db, emp_id)
    _check_department(db, data.department_id)
    for key, value in data.model_dump().items():
        setattr(emp, key, value)
    if emp.user:
        emp.user.email = emp.email.lower()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An employee with that email already exists")
    db.refresh(emp)
    return emp


@router.delete("/{emp_id}", status_code=204)
def delete_employee(emp_id: int, db: Session = Depends(get_db)):
    db.delete(_get_or_404(db, emp_id))
    db.commit()
