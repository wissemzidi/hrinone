from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, String, Text, func
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
    trainings: Mapped[list["TrainingAssignment"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    performance: Mapped[list["EmployeePerformance"]] = relationship(cascade="all, delete-orphan")
    documents: Mapped[list["DocumentRequest"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    questions: Mapped[list["HRQuestion"]] = relationship(
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
    notifications: Mapped[list["Notification"]] = relationship(cascade="all, delete-orphan")


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


# ---------- performance (monthly KPI per team, objectives per person) ----------
class PerformanceRecord(Base):
    """One KPI figure per department per month, e.g. revenue achieved vs target."""

    __tablename__ = "performance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"))
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    kpi: Mapped[str] = mapped_column(String(80))
    target: Mapped[float] = mapped_column(Float)
    achieved: Mapped[float] = mapped_column(Float)


class EmployeePerformance(Base):
    """Share of personal objectives reached in a month (0-100)."""

    __tablename__ = "employee_performance"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    month: Mapped[str] = mapped_column(String(7))
    score: Mapped[float] = mapped_column(Float)


# ---------- training ----------
class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500), default="")
    hours: Mapped[float] = mapped_column(Float, default=2)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False)

    assignments: Mapped[list["TrainingAssignment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class TrainingAssignment(Base):
    """status is stored as assigned / completed / missed. 'overdue' is derived (assigned + past due)."""

    __tablename__ = "training_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="assigned")
    due_date: Mapped[date] = mapped_column(Date)
    completed_at: Mapped[date | None] = mapped_column(Date)
    last_reminded_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="trainings")
    course: Mapped[Course] = relationship(back_populates="assignments")


# ---------- notifications ----------
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(String(400), default="")
    kind: Mapped[str] = mapped_column(String(30), default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------- HR assistant ----------
class KnowledgeDoc(Base):
    """Company documents (policies, procedures) the assistant answers from."""

    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60), default="General")
    keywords: Mapped[str] = mapped_column(String(300), default="")  # extra search words (FR / darija / synonyms)
    content: Mapped[str] = mapped_column(Text)


class DocumentRequest(Base):
    """An administrative document an employee asked for. status: ready | pending | rejected."""

    __tablename__ = "document_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    doc_type: Mapped[str] = mapped_column(String(30))
    purpose: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="documents")


class HRQuestion(Base):
    """A question the assistant could not answer, forwarded to HR by the employee."""

    __tablename__ = "hr_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="open")
    answer: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="questions")


class AuthSession(Base):
    """Opaque server-side login session; only a SHA-256 token digest is stored."""
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[str] = mapped_column(String(64), default="unknown")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SecurityEvent(Base):
    """Append-only security/audit events; never store passwords or tokens here."""
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(120), default="")
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    method: Mapped[str] = mapped_column(String(10), default="")
    path: Mapped[str] = mapped_column(String(240), default="")
    status_code: Mapped[int] = mapped_column(default=0)
    ip_address: Mapped[str] = mapped_column(String(64), default="unknown")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    details: Mapped[str] = mapped_column(String(300), default="")
