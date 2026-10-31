# hrinone

A small HR app with two roles.

- **Admin:** dashboard of who's out, people directory, approve or reject time off, recruiting (roles and ranked applications).
- **Employee:** sign in and file vacation, sick or personal leave, then track the answer.
- **Candidates (no account):** open roles page on the sign-in screen, apply with a CV (PDF, DOCX or TXT). Each CV is summarised and rated 0 to 100 against the role for the admin.

- **frontend/**: React 19 + Vite
- **backend/**: Python FastAPI + SQLAlchemy + SQLite (a sample database is created and seeded on first start)

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

## Next steps

Password reset, manager role, email notifications to candidates, Alembic migrations, and PostgreSQL plus cloud file storage for production.
