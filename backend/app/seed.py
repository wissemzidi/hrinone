"""Fills an empty database with sample data and makes sure demo logins exist."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .auth import hash_password
from .calc import first_of_month_back, month_keys

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
    ("Hichem", "Ayari", "Account Executive", "Sales", 400),
    ("Sarra", "Mejri", "Sales Representative", "Sales", 250),
    ("Walid", "Tlili", "Sales Representative", "Sales", 150),
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

    # demo data for the analytics, training and assistant features (each part only fills an empty table)
    people = {e.first_name: e for e in db.scalars(select(models.Employee)).all()}
    depts = {d.name: d for d in db.scalars(select(models.Department)).all()}
    if not db.scalar(select(models.PerformanceRecord.id).limit(1)):
        _seed_performance(db, people, depts)
    if not db.scalar(select(models.Course.id).limit(1)):
        _seed_training(db, people)
    if not db.scalar(select(models.KnowledgeDoc.id).limit(1)):
        for title, cat, keywords, content in KNOWLEDGE:
            db.add(models.KnowledgeDoc(title=title, category=cat, keywords=keywords, content=content))
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


# ---------------------------------------------------------------- analytics demo data
# KPI per team: (name, monthly target, achieved over the last 6 months, oldest first)
KPIS = {
    "Sales": ("Revenue (kTND)", 150, [148, 152, 146, 139, 128, 112]),  # sliding
    "Engineering": ("Story points delivered", 80, [76, 79, 82, 84, 86, 88]),  # improving
    "Design": ("Design deliverables", 20, [19, 20, 19, 20, 20, 19]),  # steady
    "Finance": ("Closings done on time (%)", 100, [97, 96, 98, 94, 91, 93]),  # a little down
    "People & Culture": ("HR tickets resolved", 60, [58, 61, 63, 60, 62, 64]),  # steady
}

# share of personal objectives reached, last 6 months, oldest first
PERSON_PERF = {
    "Amira": [92, 93, 94, 95, 95, 96], "Youssef": [88, 90, 91, 93, 94, 95], "Lina": [85, 87, 90, 91, 93, 94],
    "Karim": [90, 90, 91, 91, 92, 92], "Salma": [86, 88, 88, 90, 91, 92],
    "Omar": [90, 86, 80, 72, 63, 52], "Nour": [95, 94, 93, 94, 92, 90],
    "Hichem": [84, 83, 80, 76, 70, 64], "Sarra": [82, 81, 82, 79, 75, 71], "Walid": [80, 81, 79, 78, 77, 76],
    "Rania": [88, 87, 89, 86, 84, 85], "Ines": [90, 89, 88, 80, 76, 74], "Mehdi": [88, 89, 88, 89, 88, 89],
}

# unplanned absences: (person, months back, day offset in that month, working days, type)
ABSENCES = [
    ("Omar", 3, 6, 1, "sick"), ("Omar", 2, 4, 2, "sick"), ("Omar", 2, 18, 2, "personal"),
    ("Omar", 1, 3, 3, "sick"), ("Omar", 1, 15, 3, "sick"), ("Omar", 1, 24, 2, "personal"), ("Omar", 0, 0, 3, "sick"),
    ("Hichem", 2, 10, 2, "sick"), ("Hichem", 1, 8, 2, "sick"), ("Hichem", 0, 1, 2, "personal"),
    ("Sarra", 1, 20, 1, "sick"), ("Ines", 1, 12, 2, "sick"), ("Ines", 0, 0, 1, "sick"),
    ("Youssef", 3, 10, 1, "sick"), ("Lina", 2, 7, 1, "sick"), ("Rania", 4, 9, 1, "sick"),
]


def _seed_performance(db: Session, people: dict, depts: dict) -> None:
    today = date.today()
    months = month_keys(6, today)
    for dept_name, (kpi, target, achieved) in KPIS.items():
        if dept_name in depts:
            for m, a in zip(months, achieved):
                db.add(models.PerformanceRecord(department_id=depts[dept_name].id, month=m, kpi=kpi, target=target, achieved=a))
    for first, scores in PERSON_PERF.items():
        if first in people:
            for m, sc in zip(months, scores):
                db.add(models.EmployeePerformance(employee_id=people[first].id, month=m, score=sc))
    for first, back, offset, length, kind in ABSENCES:
        if first not in people:
            continue
        start = first_of_month_back(back, today) + timedelta(days=offset)
        end = start + timedelta(days=length - 1)
        if back == 0:  # this month: only days that already happened
            end = min(end, today - timedelta(days=1))
        if start > end:
            continue
        db.add(models.LeaveRequest(employee_id=people[first].id, leave_type=kind, status="approved",
                                   start_date=start, end_date=end, reason="Absence"))


# ---------------------------------------------------------------- training demo data
COURSES = [
    ("Cybersecurity Awareness", "Phishing, passwords and safe handling of company data.", 1.5, True),
    ("Negotiation & Closing Deals", "Structure a negotiation and close with confidence.", 6, False),
    ("CRM Essentials", "Keep your pipeline clean and forecasts reliable.", 4, False),
    ("Time Management & Priorities", "Plan your week around what matters.", 3, False),
    ("Advanced React Patterns", "Hooks, performance and testing for React teams.", 8, False),
    ("Leadership Basics", "Feedback, delegation and one-to-ones.", 6, False),
    ("Excel for Finance Teams", "Models, pivots and reconciliations.", 4, False),
    ("UX Research Methods", "Interviews, usability tests and synthesis.", 6, False),
]

# (person, course, status, due in days (negative = past), completed N days ago)
ASSIGNMENTS = [
    ("Omar", "Cybersecurity Awareness", "assigned", -20, None), ("Hichem", "Cybersecurity Awareness", "missed", -20, None),
    ("Sarra", "Cybersecurity Awareness", "completed", -20, 25), ("Walid", "Cybersecurity Awareness", "assigned", -20, None),
    ("Nour", "Cybersecurity Awareness", "completed", -20, 30),
    ("Omar", "Negotiation & Closing Deals", "missed", -30, None), ("Hichem", "Negotiation & Closing Deals", "missed", -30, None),
    ("Sarra", "Negotiation & Closing Deals", "assigned", -30, None), ("Walid", "Negotiation & Closing Deals", "completed", -30, 40),
    ("Nour", "Negotiation & Closing Deals", "completed", -30, 45),
    ("Omar", "CRM Essentials", "assigned", -10, None), ("Hichem", "CRM Essentials", "assigned", -10, None),
    ("Sarra", "CRM Essentials", "completed", -10, 14),
    ("Amira", "Cybersecurity Awareness", "completed", -20, 33), ("Youssef", "Cybersecurity Awareness", "completed", -20, 28),
    ("Lina", "Cybersecurity Awareness", "completed", -20, 27), ("Youssef", "Advanced React Patterns", "completed", -45, 60),
    ("Lina", "Advanced React Patterns", "completed", -45, 55), ("Amira", "Leadership Basics", "completed", -60, 70),
    ("Youssef", "Time Management & Priorities", "completed", -35, 41), ("Lina", "Leadership Basics", "assigned", 14, None),
    ("Rania", "Cybersecurity Awareness", "completed", -20, 26), ("Rania", "Excel for Finance Teams", "completed", -40, 52),
    ("Ines", "Cybersecurity Awareness", "completed", -20, 22), ("Ines", "Excel for Finance Teams", "assigned", -12, None),
    ("Mehdi", "Cybersecurity Awareness", "completed", -20, 24), ("Mehdi", "UX Research Methods", "completed", -50, 58),
    ("Karim", "Cybersecurity Awareness", "completed", -20, 29), ("Karim", "Leadership Basics", "completed", -70, 80),
    ("Salma", "Cybersecurity Awareness", "completed", -20, 31), ("Salma", "Time Management & Priorities", "completed", -30, 36),
]


def _seed_training(db: Session, people: dict) -> None:
    today = date.today()
    courses = {}
    for title, desc, hours, mandatory in COURSES:
        courses[title] = models.Course(title=title, description=desc, hours=hours, mandatory=mandatory)
    db.add_all(courses.values())
    db.flush()
    for first, title, status, due, done_ago in ASSIGNMENTS:
        if first not in people:
            continue
        db.add(models.TrainingAssignment(
            employee_id=people[first].id, course_id=courses[title].id, status=status,
            due_date=today + timedelta(days=due),
            completed_at=today - timedelta(days=done_ago) if done_ago else None))


# ---------------------------------------------------------------- company documents for the assistant
# Sample policies for the demo: replace them with the real ones from the Requests > Knowledge base page.
KNOWLEDGE = [
    ("Vacation policy", "Leave", "conge conges vacances holiday annual leave jours solde balance 3utla vacation entitlement",
     "Every full-time employee receives 21 working days of paid vacation per calendar year.\n"
     "Vacation requests must be submitted on the Time off page at least 7 days before the start date. Your manager and HR approve or reject the request.\n"
     "Up to 5 unused vacation days can be carried over to the next year and must be used before 31 March."),
    ("Sick leave", "Leave", "maladie malade medical certificat arret travail mourid sick ill doctor",
     "If you are sick, tell your manager as early as possible on the first day and submit a sick leave request in the app.\n"
     "A medical certificate is required for any absence longer than 2 consecutive days. Medical documents are handled confidentially by HR."),
    ("Parental leave", "Leave", "maternite paternite maternity paternity naissance baby bebe parental",
     "Maternity leave is 30 days and paternity leave is 5 working days, fully paid. Submit a parental leave request with the birth certificate."),
    ("Remote work", "Working time", "teletravail remote home maison work from home telework",
     "Employees may work remotely up to 2 days per week, agreed with their manager.\n"
     "Remote days must be announced the day before. Roles tied to a client site follow the team rota."),
    ("Working hours", "Working time", "horaires heures hours overtime supplementaires pause lunch",
     "Core hours are 9:00 to 17:00, Monday to Friday, with a one hour lunch break.\n"
     "Overtime must be approved in advance by your manager."),
    ("Expense reimbursement", "Finance", "frais remboursement expenses notes de frais receipts recus travel deplacement",
     "Business expenses are reimbursed within 30 days when submitted with receipts.\n"
     "Travel must be pre-approved by your manager. Send your claims to Finance before the 25th of the month."),
    ("Payroll", "Finance", "paie salaire salary payslip fiche de paie paiement virement pay payday",
     "Salaries are paid on the 28th of each month by bank transfer. If the 28th is a weekend, payment is made the previous working day.\n"
     "Payslips are available from Finance on the payment day."),
    ("Training policy", "Development", "formation formations training cours learning mandatory obligatoire",
     "Each employee is entitled to at least 20 hours of paid training per year.\n"
     "Mandatory trainings, such as Cybersecurity Awareness, must be completed before their due date.\n"
     "If you cannot attend a session, tell HR at least 48 hours ahead so it can be rescheduled."),
    ("Administrative documents", "HR services", "attestation certificat document papier work certificate salary letter",
     "Work certificates, leave summaries and training records are generated instantly by the HR assistant. Ask for example: I need a work certificate.\n"
     "Salary certificates need HR approval and are usually ready within 2 working days."),
]
