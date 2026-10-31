from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- departments ----------
class DepartmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class DepartmentOut(ORM, DepartmentIn):
    id: int


# ---------- employees ----------
class EmployeeIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    job_title: str = Field(min_length=1, max_length=100)
    hire_date: date
    status: Literal["active", "inactive"] = "active"
    department_id: int | None = None


class EmployeeCreate(EmployeeIn):
    password: str = Field(min_length=6, max_length=100)


class EmployeeOut(ORM, EmployeeIn):
    id: int
    department: DepartmentOut | None = None


class EmployeeBrief(ORM):
    id: int
    first_name: str
    last_name: str
    job_title: str


# ---------- auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(ORM):
    id: int
    email: str
    role: Literal["admin", "employee"]
    employee: EmployeeBrief | None = None


class LoginOut(BaseModel):
    token: str
    user: UserOut


# ---------- leave ----------
LeaveType = Literal["vacation", "sick", "personal", "parental"]


class LeaveIn(BaseModel):
    employee_id: int | None = None  # admins choose; employees always file for themselves
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date can't be before the start date")
        return self


class LeaveDecision(BaseModel):
    status: Literal["approved", "rejected"]


class LeaveOut(ORM):
    id: int
    employee: EmployeeBrief
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str
    status: Literal["pending", "approved", "rejected"]
    created_at: datetime


# ---------- recruiting ----------
class JobIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    department: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=4000)
    required_skills: list[str] = []
    min_years: int = Field(default=0, ge=0, le=40)
    status: Literal["open", "closed"] = "open"


class JobOut(ORM):
    id: int
    title: str
    department: str
    description: str
    required_skills: list[str]
    min_years: int
    status: Literal["open", "closed"]

    @field_validator("required_skills", mode="before")
    @classmethod
    def split_skills(cls, v):
        return [s.strip() for s in v.split(",") if s.strip()] if isinstance(v, str) else v


class JobAdminOut(JobOut):
    application_count: int


class JobBrief(ORM):
    id: int
    title: str


class ApplicationOut(ORM):
    id: int
    job: JobBrief
    candidate_name: str
    candidate_email: str
    cover_note: str
    cv_filename: str
    status: Literal["new", "shortlisted", "rejected"]
    score: int
    analysis: dict
    created_at: datetime


class ApplicationStatus(BaseModel):
    status: Literal["new", "shortlisted", "rejected"]
