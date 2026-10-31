"""Fills an empty database with sample data and makes sure demo logins exist."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .auth import hash_password

ADMIN_EMAIL, ADMIN_PASSWORD = "admin@hrinone.app", "admin123"
EMPLOYEE_PASSWORD = "welcome123"

DEPARTMENTS = ["Engineering", "People & Culture", "Sales", "Finance", "Design"]

EMPLOYEES = [
    ("Amira", "Ben Salah", "Engineering Manager", "Engineering", 1800),
    ("Youssef", "Trabelsi", "Backend Developer", "Engineering", 900),
    ("Lina", "Haddad", "Frontend Developer", "Engineering", 500),
    ("Karim", "Mansour", "Head of People", "People & Culture", 2400),
    ("Salma", "Jaziri", "Recruiter", "People & Culture", 300),
    ("Omar", "Gharbi", "Account Executive", "Sales", 700),
    ("Nour", "Chaabane", "Sales Lead", "Sales", 1500),
    ("Rania", "Bouzid", "Financial Controller", "Finance", 1200),
    ("Mehdi", "Khelifi", "Product Designer", "Design", 650),
    ("Ines", "Dridi", "Payroll Specialist", "Finance", 200),
]

JOBS = [
    ("Backend Developer", "Engineering", "Build and run the APIs behind our HR products.",
     "python,fastapi,sql,docker,git", 3),
    ("Product Designer", "Design", "Design flows for people who manage work and time off.",
     "figma,user research,prototyping,css", 2),
]


def seed(db: Session) -> None:
    if not db.scalar(select(models.Employee.id).limit(1)):
        _seed_people(db)

    # accounts: one admin, and a login for every employee that lacks one
    if not db.scalar(select(models.User).where(models.User.email == ADMIN_EMAIL)):
        db.add(models.User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), role="admin"))
    shared_hash = hash_password(EMPLOYEE_PASSWORD)
    for emp in db.scalars(select(models.Employee)).all():
        if not emp.user:
            emp.user = models.User(email=emp.email.lower(), password_hash=shared_hash, role="employee")

    if not db.scalar(select(models.Job.id).limit(1)):
        for title, dept, desc, skills, years in JOBS:
            db.add(models.Job(title=title, department=dept, description=desc, required_skills=skills, min_years=years))
    db.commit()


def _seed_people(db: Session) -> None:
    depts = {name: models.Department(name=name) for name in DEPARTMENTS}
    db.add_all(depts.values())
    db.flush()

    today = date.today()
    emps = []
    for first, last, title, dept, days_ago in EMPLOYEES:
        emps.append(
            models.Employee(
                first_name=first,
                last_name=last,
                email=f"{first}.{last}".lower().replace(" ", "") + "@hrinone.app",
                job_title=title,
                hire_date=today - timedelta(days=days_ago),
                department_id=depts[dept].id,
            )
        )
    db.add_all(emps)
    db.flush()

    d = timedelta
    db.add_all(
        [
            models.LeaveRequest(employee_id=emps[1].id, leave_type="vacation", status="approved",
                                start_date=today - d(days=1), end_date=today + d(days=3), reason="Family trip"),
            models.LeaveRequest(employee_id=emps[5].id, leave_type="sick", status="approved",
                                start_date=today, end_date=today + d(days=1), reason="Flu"),
            models.LeaveRequest(employee_id=emps[2].id, leave_type="vacation", status="pending",
                                start_date=today + d(days=14), end_date=today + d(days=21), reason="Summer break"),
            models.LeaveRequest(employee_id=emps[8].id, leave_type="personal", status="pending",
                                start_date=today + d(days=5), end_date=today + d(days=5), reason="Moving flat"),
            models.LeaveRequest(employee_id=emps[7].id, leave_type="vacation", status="rejected",
                                start_date=today + d(days=30), end_date=today + d(days=40), reason="Quarter close overlap"),
        ]
    )
