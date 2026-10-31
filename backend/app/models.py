from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(60))
    last_name: Mapped[str] = mapped_column(String(60))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    job_title: Mapped[str] = mapped_column(String(100))
    hire_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"))

    department: Mapped[Department | None] = relationship()
    user: Mapped["User | None"] = relationship(
        back_populates="employee", cascade="all, delete-orphan", uselist=False
    )
    leaves: Mapped[list["LeaveRequest"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class User(Base):
    """A login. role is 'admin' or 'employee'; employees link to their Employee record."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="employee")
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))

    employee: Mapped[Employee | None] = relationship(back_populates="user")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    leave_type: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="leaves")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[str] = mapped_column(String(500), default="")  # comma separated
    min_years: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    @property
    def skills_list(self) -> list[str]:
        return [s.strip() for s in self.required_skills.split(",") if s.strip()]

    @property
    def application_count(self) -> int:
        return len(self.applications)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    candidate_name: Mapped[str] = mapped_column(String(120))
    candidate_email: Mapped[str] = mapped_column(String(120))
    cover_note: Mapped[str] = mapped_column(String(1000), default="")
    cv_filename: Mapped[str] = mapped_column(String(200))  # original name, for downloads
    cv_path: Mapped[str] = mapped_column(String(100))  # name inside the uploads folder
    status: Mapped[str] = mapped_column(String(20), default="new")
    score: Mapped[int] = mapped_column(default=0)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    job: Mapped[Job] = relationship(back_populates="applications")
