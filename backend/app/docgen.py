"""Builds the administrative documents (Word .docx) from the HR record.

Everything in a document comes from the database (or from the figure HR typed when approving a
salary certificate). Nothing is invented by a model, so the document is safe to hand out.
"""
import io
from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from . import models
from .calc import effective_status, overlap_weekdays

COMPANY = "hrinone"
ANNUAL_VACATION_DAYS = 21  # keep in sync with the vacation policy in seed.py

DOC_TYPES = {
    # auto = produced instantly from HR records (low risk, factual); otherwise HR approves first
    "work_certificate": {"label": "Work certificate", "auto": True},
    "leave_summary": {"label": "Leave summary", "auto": True},
    "training_record": {"label": "Training record", "auto": True},
    "salary_certificate": {"label": "Salary certificate", "auto": False},
}


def vacation_balance(employee: models.Employee, today: date | None = None) -> dict:
    today = today or date.today()
    y0, y1 = date(today.year, 1, 1), date(today.year, 12, 31)
    used = pending = 0
    for lv in employee.leaves:
        if lv.leave_type != "vacation":
            continue
        days = overlap_weekdays(lv.start_date, lv.end_date, y0, y1)
        if lv.status == "approved":
            used += days
        elif lv.status == "pending":
            pending += days
    return {"entitlement": ANNUAL_VACATION_DAYS, "used": used, "pending": pending,
            "remaining": ANNUAL_VACATION_DAYS - used}


def _fmt(d: date) -> str:
    return d.strftime("%d %B %Y")


def _table(doc: Document, header: list[str], rows: list[list[str]]) -> None:
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = h
        for r in t.rows[0].cells[i].paragraphs[0].runs:
            r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v


def build_docx(req: models.DocumentRequest, today: date | None = None) -> bytes:
    today = today or date.today()
    emp = req.employee
    name = f"{emp.first_name} {emp.last_name}"
    dept = emp.department.name if emp.department else "the company"
    meta = DOC_TYPES[req.doc_type]

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    head = doc.add_paragraph()
    run = head.add_run(COMPANY)
    run.bold = True
    run.font.size = Pt(18)
    doc.add_paragraph("Human Resources Department")
    doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t = title.add_run(meta["label"].upper())
    t.bold = True
    t.font.size = Pt(16)
    doc.add_paragraph()

    if req.doc_type == "work_certificate":
        doc.add_paragraph(
            f"We certify that {name} has been employed at {COMPANY} since {_fmt(emp.hire_date)} and currently "
            f"holds the position of {emp.job_title} in the {dept} department."
        )
        doc.add_paragraph("This certificate is issued at the employee's request for administrative purposes.")
    elif req.doc_type == "salary_certificate":
        salary = (req.details or {}).get("salary", "")
        doc.add_paragraph(
            f"We certify that {name}, {emp.job_title}, employed at {COMPANY} since {_fmt(emp.hire_date)}, "
            f"receives a salary of {salary}."
        )
        doc.add_paragraph("This certificate is issued at the employee's request and was approved by Human Resources.")
    elif req.doc_type == "leave_summary":
        bal = vacation_balance(emp, today)
        doc.add_paragraph(f"Leave summary for {name} ({emp.job_title}), year {today.year}.")
        _table(doc, ["Item", "Working days"], [
            ["Annual vacation entitlement", str(bal["entitlement"])],
            ["Vacation taken (approved)", str(bal["used"])],
            ["Vacation waiting for approval", str(bal["pending"])],
            ["Vacation remaining", str(bal["remaining"])],
        ])
        y0, y1 = date(today.year, 1, 1), date(today.year, 12, 31)
        other = {}
        for lv in emp.leaves:
            if lv.status == "approved" and lv.leave_type != "vacation":
                other[lv.leave_type] = other.get(lv.leave_type, 0) + overlap_weekdays(lv.start_date, lv.end_date, y0, y1)
        if other:
            doc.add_paragraph()
            doc.add_paragraph("Other approved leave this year:")
            _table(doc, ["Type", "Working days"], [[k.capitalize(), str(v)] for k, v in other.items()])
    elif req.doc_type == "training_record":
        rows = [
            [a.course.title, f"{a.course.hours:g} h", _fmt(a.completed_at) if a.completed_at else "-"]
            for a in sorted(emp.trainings, key=lambda a: a.completed_at or date.min, reverse=True)
            if a.status == "completed"
        ]
        total_h = sum(a.course.hours for a in emp.trainings if a.status == "completed")
        doc.add_paragraph(f"Trainings completed by {name} ({emp.job_title}).")
        if rows:
            _table(doc, ["Course", "Duration", "Completed on"], rows)
            doc.add_paragraph()
            doc.add_paragraph(f"Total: {len(rows)} trainings, {total_h:g} hours.")
        else:
            doc.add_paragraph("No completed trainings are recorded yet.")

    doc.add_paragraph()
    doc.add_paragraph(f"Issued on {_fmt(today)}")
    ref = doc.add_paragraph(f"Reference: HR-{req.id:05d}")
    ref.runs[0].font.size = Pt(9)
    note = doc.add_paragraph(
        "Prepared automatically by the HR assistant from the HR record."
        + ("" if meta["auto"] else " Approved by Human Resources.")
    )
    note.runs[0].font.size = Pt(9)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
