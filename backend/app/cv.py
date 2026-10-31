"""Reads a CV, summarises it and scores it against a job.

This is a transparent rule-based analyser (skills, years of experience, education),
so it works offline. The two public functions can be swapped for an LLM call later
without touching the rest of the app.
"""
import io
import re

from fastapi import HTTPException

# Used to list extra skills the candidate mentions beyond the job's requirements.
SKILL_VOCAB = [
    "python", "java", "javascript", "typescript", "react", "vue", "angular", "node.js", "fastapi",
    "django", "flask", "sql", "postgresql", "mysql", "mongodb", "docker", "kubernetes", "aws", "azure",
    "git", "ci/cd", "linux", "html", "css", "figma", "user research", "prototyping", "c#", "c++", "go",
    "excel", "payroll", "recruiting", "negotiation", "crm", "accounting", "project management", "agile",
    "communication", "leadership",
]

EDUCATION = [  # (label, level, keywords)
    ("PhD", 3, ["phd", "ph.d", "doctorate"]),
    ("Master's degree", 3, ["master", "msc", "m.sc", "mba"]),
    ("Bachelor's degree", 2, ["bachelor", "bsc", "b.sc", "licence", "licentiate", "engineering degree"]),
    ("Diploma", 1, ["diploma", "associate degree"]),
]


def extract_text(ext: str, data: bytes) -> str:
    try:
        if ext == ".pdf":
            from pypdf import PdfReader

            text = " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        elif ext == ".docx":
            import docx

            text = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
        else:
            text = data.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(422, "We couldn't read that file. Try exporting your CV as a PDF or DOCX again")
    if len(text.strip()) < 30:
        raise HTTPException(422, "We couldn't find any text in that CV. Scanned images aren't supported")
    return text


# A candidate who lists one of these clearly has the skill on the left.
ALIASES = {
    "sql": ["postgresql", "postgres", "mysql", "sqlite"],
    "javascript": ["js", "typescript"],
    "node.js": ["node", "nodejs"],
    "aws": ["amazon web services"],
    "ci/cd": ["github actions", "gitlab ci", "jenkins"],
    "user research": ["usability testing", "user interviews"],
}


def _has(text: str, skill: str) -> bool:
    for term in [skill.lower(), *ALIASES.get(skill.lower(), [])]:
        if re.search(rf"(?<![\w+#]){re.escape(term)}(?!\w)", text):
            return True
    return False


def analyze(text: str, required_skills: list[str], min_years: int) -> dict:
    low = text.lower()

    matched = [s for s in required_skills if _has(low, s)]
    missing = [s for s in required_skills if s not in matched]
    others = [s for s in SKILL_VOCAB if _has(low, s) and s.lower() not in {m.lower() for m in matched}]

    year_hits = [int(y) for y in re.findall(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", low)]
    years = min(max(year_hits, default=0), 40)

    edu_label, edu_level = "", 0
    for label, level, words in EDUCATION:
        if level > edu_level and any(_has(low, w) for w in words):
            edu_label, edu_level = label, level

    skills_share = len(matched) / len(required_skills) if required_skills else min(len(others) / 8, 1)
    exp_target = min_years if min_years > 0 else 3
    exp_share = min(years / exp_target, 1)
    edu_share = min(edu_level / 3, 1)
    breakdown = {
        "skills": round(60 * skills_share),
        "experience": round(30 * exp_share),
        "education": round(10 * edu_share),
    }
    score = sum(breakdown.values())
    label = "Strong match" if score >= 75 else "Possible match" if score >= 50 else "Weak match"

    parts = []
    if required_skills:
        parts.append(f"Covers {len(matched)} of {len(required_skills)} required skills.")
    parts.append(f"States about {years} years of experience." if years else "Doesn't state years of experience.")
    if edu_label:
        parts.append(f"Highest qualification found: {edu_label}.")
    if others:
        parts.append("Also mentions " + ", ".join(others[:6]) + ".")

    return {
        "score": score,
        "label": label,
        "summary": " ".join(parts),
        "matched_skills": matched,
        "missing_skills": missing,
        "other_skills": others[:10],
        "years_experience": years,
        "education": edu_label,
        "breakdown": breakdown,
    }
