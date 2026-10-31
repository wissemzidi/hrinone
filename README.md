# hrinone

A small HR app with two roles.

- **Admin:** dashboard of who's out, people directory, approve or reject time off, recruiting (roles and ranked applications).
- **Employee:** sign in and file vacation, sick or personal leave, then track the answer.
- **Candidates (no account):** open roles page on the sign-in screen, apply with a CV (PDF, DOCX or TXT). Each CV is summarised and rated 0 to 100 against the role for the admin.

- **frontend/**: React 19 + Vite
- **backend/**: Python FastAPI + SQLAlchemy + SQLite (a sample database is created and seeded on first start)

## What's new in v0.2

**Admin**
- **Dashboard → Company health:** company result vs target (average of the teams), trend, absence rate, training completion, what is waiting for HR, and a chip per team with its ▲/▼ trend.
- **Performance:** one card per team (any department with monthly KPI figures): % of target, **up/down indicator** vs last month, status (on track / watch / off track) and a **value-added verdict**. Click a team for the full analysis: 6-month chart, absence rate, training completion, **likely causes** ranked with the numbers behind them (absences, training gap, individuals dropping) and **suggested solutions**. If an AI key is set (see below), an AI model also writes the analysis (names are replaced by labels before anything leaves the server); without a key a rule-based summary is shown, so the demo never breaks.
- **Training:** create courses, assign them to people or a whole department (everyone gets a notification), mark completed / missed (a missed training notifies the employee), **Remind overdue** in one click, and see **how many trainings each person completed** (also shown on the People page).
- **Requests:** approve documents that need HR (salary certificate), answer questions the assistant could not handle, and edit the **knowledge base** (company documents) the assistant answers from.

**Employee**
- **My training:** completed / upcoming / overdue, hours learned.
- **HR assistant:** answers leave, pay and policy questions from the company documents, personal questions (vacation days left, trainings done) from the employee's own file, and **generates administrative documents automatically** (work certificate, leave summary, training record as Word files). Anything it can't answer can be forwarded to HR with one click.
- **Notifications** bell for both roles.

**Human in the loop:** the AI only suggests (analysis, answers) and prepares (documents). Nothing about a person is decided or recorded by the AI: HR assigns trainings, marks them missed, approves salary certificates and answers escalated questions.

**Security added:** login rate limiting, assistant rate limiting, security headers, employees can only read their own data and documents (a document that isn't yours answers 404), assistant input is length-capped and passed to the model as untrusted data in tags, personal data is pseudonymised before any LLM call, and the LLM is optional.

> New tables are added automatically, but the demo data (6 months of KPIs, trainings, sample policies, 3 extra sales people) is only created on a fresh database. If you already ran v0.1, delete `backend/hrinone.db` and restart.

**AI model (optional).** Put the key in `backend/.env` (copy `backend/.env.example`; the file is ignored by git and is never sent to the browser):

```
GEMINI_API_KEY=your-key        # Google Gemini, or use ANTHROPIC_API_KEY for Anthropic
# HRINONE_MODEL=gemini-flash-latest
```

Restart the backend, then check it with `python check_llm.py` (inside `backend`) or open `http://localhost:8000/api/health`, which shows the active provider. Without a key the app keeps using its rule-based answers.

## Demo logins

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@hrinone.app` | `admin123` |
| Employee | `youssef.trabelsi@hrinone.app` (any seeded person: `first.last@hrinone.app`) | `welcome123` |

Change these before using the app for real, and set a private signing key: `HRINONE_SECRET=some-long-random-string`.

## Run it

Backend (http://localhost:8000, interactive API docs at `/docs`):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend (http://localhost:5173):

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to the backend, so no extra configuration is needed in development.

## How CV rating works

`backend/app/cv.py` reads the text from the CV and scores it out of 100: **60** for the required skills it mentions (with aliases, e.g. PostgreSQL counts as SQL), **30** for years of experience against the role's minimum, **10** for education. The admin sees the score, a short summary, matched and missing skills, and the breakdown. It is a keyword-based estimate to help sort applications, not a hiring decision. Scanned (image-only) PDFs can't be read. `analyze()` and `extract_text()` can be replaced with an LLM call later without changing anything else.

## How the team analysis works

`backend/app/insights.py` (plain Python, no database): attainment = achieved / target. Trend is ▲ / ▼ when the month-on-month move is at least 2 points. Status: ≥100% on track, 90-100% watch, <90% off track. When a team is below target or sliding, it looks for three causes and ranks them by severity: **absences** (unplanned sick/personal days over the last 2 months vs the company), **training gap** (completion rate vs the company, and whether people with outstanding trainings reach fewer objectives), **individuals** (objectives under 70% or down 15 points in 3 months, cross-checked with their absences and trainings). Each cause carries its evidence and concrete actions.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/login` | Sign in, returns a token (send it as `Authorization: Bearer ...`) |
| GET | `/api/auth/me` | Current user |
| GET | `/api/jobs` | Public: open roles |
| POST | `/api/applications` | Public: apply with a CV (multipart form) |
| GET, POST, PUT, DELETE | `/api/jobs/manage`, `/api/jobs/{id}` | Admin: manage roles |
| GET, PATCH, DELETE | `/api/applications`, `/api/applications/{id}` | Admin: ranked applications, shortlist or reject |
| GET | `/api/applications/{id}/cv` | Admin: download the CV |
| GET | `/api/stats` | Dashboard: who's out today, pending requests, headcount by department |
| GET, POST | `/api/employees` | List (`search`, `department_id`, `status`) / create |
| GET, PUT, DELETE | `/api/employees/{id}` | Read / update / remove |
| GET, POST | `/api/departments` | List / create |
| DELETE | `/api/departments/{id}` | Remove |
| GET, POST | `/api/leaves` | List (`status`, `employee_id`) / create |
| PATCH | `/api/leaves/{id}` | Approve or reject (`{"status": "approved"}`) |
| DELETE | `/api/leaves/{id}` | Delete |
| GET | `/api/analytics/company`, `/api/analytics/teams`, `/api/analytics/teams/{id}?ai=true` | Admin: company health, team cards, full diagnosis |
| GET, POST, DELETE | `/api/training/courses` | Admin: courses |
| GET, POST, PATCH, DELETE | `/api/training/assignments`, `/api/training/assign`, `/api/training/remind`, `/api/training/overview` | Admin: assign, track, remind |
| GET | `/api/training/mine` | Employee: my trainings |
| GET | `/api/notifications`, POST `/api/notifications/read-all` | Own notifications |
| POST | `/api/assistant/ask`, `/api/assistant/escalate` | Employee: ask the assistant / forward to HR |
| GET, PATCH | `/api/assistant/questions` | Admin: answer forwarded questions |
| GET, POST, PUT, DELETE | `/api/knowledge` | Admin: company documents |
| POST, GET | `/api/documents`, `/api/documents/mine`, `/api/documents/{id}/download` | Request and download documents |
| GET, PATCH | `/api/documents`, `/api/documents/{id}` | Admin: approve or decline

## Next steps

Password reset, manager role, email notifications to candidates, Alembic migrations, and PostgreSQL plus cloud file storage for production.
