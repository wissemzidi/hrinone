from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import admin_only
from ..database import get_db

router = APIRouter(prefix="/departments", tags=["departments"], dependencies=[Depends(admin_only)])


@router.get("", response_model=list[schemas.DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.scalars(select(models.Department).order_by(models.Department.name)).all()


@router.post("", response_model=schemas.DepartmentOut, status_code=201)
def create_department(data: schemas.DepartmentIn, db: Session = Depends(get_db)):
    if db.scalar(select(models.Department).where(models.Department.name == data.name)):
        raise HTTPException(409, "A department with that name already exists")
    dept = models.Department(name=data.name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{dept_id}", status_code=204)
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    dept = db.get(models.Department, dept_id)
    if not dept:
        raise HTTPException(404, "Department not found")
    db.delete(dept)
    db.commit()
