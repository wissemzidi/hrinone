import { useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty, Modal, Notice, Person } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { TRAINING_LABEL, TRAINING_TONE, fmtDate, fullName, todayISO } from '../utils.js'

function AssignForm({ courses, departments, people, onSaved, onClose }) {
  const [form, setForm] = useState({ course_id: courses[0]?.id ?? '', mode: 'department', department_id: departments[0]?.id ?? '', due_date: todayISO() })
  const [picked, setPicked] = useState([])
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]))

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const res = await api.post('/training/assign', {
        course_id: Number(form.course_id),
        due_date: form.due_date,
        ...(form.mode === 'department' ? { department_id: Number(form.department_id) } : { employee_ids: picked }),
      })
      onSaved(res)
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <Modal title="Assign a training" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Course
          <select required value={form.course_id} onChange={set('course_id')}>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>{c.title} ({c.hours} h)</option>
            ))}
          </select>
        </label>
        <label>
          Who
          <select value={form.mode} onChange={set('mode')}>
            <option value="department">A whole department</option>
            <option value="people">Chosen people</option>
          </select>
        </label>
        {form.mode === 'department' ? (
          <label>
            Department
            <select value={form.department_id} onChange={set('department_id')}>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </label>
        ) : (
          <fieldset className="pick-list">
            <legend>People</legend>
            {people.map((p) => (
              <label key={p.id} className="check">
                <input type="checkbox" checked={picked.includes(p.id)} onChange={() => toggle(p.id)} />
                {fullName(p)} <span className="muted small">· {p.department?.name ?? 'No department'}</span>
              </label>
            ))}
          </fieldset>
        )}
        <label>
          Due date
          <input required type="date" min={todayISO()} value={form.due_date} onChange={set('due_date')} />
        </label>
        <p className="muted small">Each person gets a notification. People who already have this course open are skipped.</p>
        {error && <p className="form-error">{error}</p>}
        <footer className="form-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={saving}>{saving ? 'Assigning…' : 'Assign and notify'}</button>
        </footer>
      </form>
    </Modal>
  )
}

function CourseForm({ onSaved, onClose }) {
  const [form, setForm] = useState({ title: '', description: '', hours: 2, mandatory: false })
  const [error, setError] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const submit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/training/courses', { ...form, hours: Number(form.hours) })
      onSaved()
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <Modal title="New course" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>Title<input required maxLength={120} value={form.title} onChange={set('title')} /></label>
        <label>Description<input maxLength={500} value={form.description} onChange={set('description')} /></label>
        <div className="form-row">
          <label>Hours<input required type="number" min="0.5" step="0.5" value={form.hours} onChange={set('hours')} /></label>
          <label className="check inline">
            <input type="checkbox" checked={form.mandatory} onChange={set('mandatory')} /> Mandatory
          </label>
        </div>
        {error && <p className="form-error">{error}</p>}
        <footer className="form-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary">Create course</button>
        </footer>
      </form>
    </Modal>
  )
}

export default function Training() {
  const [tab, setTab] = useState('assignments')
  const [status, setStatus] = useState('')
  const [dept, setDept] = useState('')
  const [modal, setModal] = useState(null) // 'assign' | 'course'
  const [flash, setFlash] = useState(null)

  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (dept) params.set('department_id', dept)
  const { data: items, error, loading, reload } = useApi(`/training/assignments?${params}`)
  const { data: overview, reload: reloadOverview } = useApi('/training/overview')
  const { data: courses, reload: reloadCourses } = useApi('/training/courses')
  const { data: departments } = useApi('/departments')
  const { data: people } = useApi('/employees?status=active')

  const refresh = () => {
    reload()
    reloadOverview()
    reloadCourses()
  }
  const mark = async (id, s) => {
    await api.patch(`/training/assignments/${id}`, { status: s })
    refresh()
  }
  const remind = async () => {
    const res = await api.post('/training/remind', { department_id: dept ? Number(dept) : null })
    setFlash(res.reminded ? `Reminder sent to ${res.reminded} ${res.reminded === 1 ? 'person' : 'people'}.` : 'Nobody to remind: everyone overdue was already reminded today.')
    refresh()
  }
  const removeCourse = async (c) => {
    if (!window.confirm(`Delete “${c.title}” and its ${c.assigned} assignments?`)) return
    await api.del(`/training/courses/${c.id}`)
    refresh()
  }

  const t = overview?.totals
  const rate = t && t.assigned ? Math.round((t.completed / t.assigned) * 100) : 0

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">Learning</div>
          <h1>Training</h1>
          <p className="muted">Program trainings, follow who did them, and nudge people who fall behind.</p>
        </div>
        <div className="actions">
          <button className="btn" onClick={remind}>Remind overdue</button>
          <button className="btn btn-primary" onClick={() => setModal('assign')} disabled={!courses?.length}>Assign training</button>
        </div>
      </header>

      {flash && <div className="flash" role="status">{flash} <button className="link" onClick={() => setFlash(null)}>Dismiss</button></div>}

      {t && (
        <div className="stats-grid">
          <article className="stat-card"><div className="stat-value">{t.assigned}</div><div className="stat-label">Assigned</div></article>
          <article className="stat-card"><div className="stat-value">{rate}%</div><div className="stat-label">Completed</div><small className="stat-note">{t.completed} done</small></article>
          <article className="stat-card"><div className="stat-value">{t.overdue}</div><div className="stat-label">Overdue</div><small className="stat-note">Past due date</small></article>
          <article className="stat-card"><div className="stat-value">{t.missed}</div><div className="stat-label">Missed</div><small className="stat-note">Marked by HR</small></article>
        </div>
      )}

      <div className="tabs" role="tablist" style={{ marginTop: 20 }}>
        {[['assignments', 'Assignments'], ['people', 'By person'], ['courses', 'Courses']].map(([id, label]) => (
          <button key={id} role="tab" aria-selected={tab === id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      {error && <Notice error={error} onRetry={refresh} />}

      {tab === 'assignments' && (
        <>
          <div className="toolbar">
            <select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All statuses</option>
              {Object.entries(TRAINING_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select aria-label="Filter by department" value={dept} onChange={(e) => setDept(e.target.value)}>
              <option value="">All departments</option>
              {(departments ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          {loading && <p className="muted">Loading…</p>}
          {items && items.length === 0 && <Empty title="No trainings here">Assign a training to see it tracked.</Empty>}
          {items && items.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Person</th><th>Course</th><th>Due</th><th>Status</th><th /></tr></thead>
                <tbody>
                  {items.map((a) => (
                    <tr key={a.id}>
                      <td><Person person={a.employee} sub={a.department ?? a.employee.job_title} /></td>
                      <td>{a.course.title}{a.course.mandatory && <Badge tone="plain"> Mandatory</Badge>}<div className="muted small">{a.course.hours} h</div></td>
                      <td>{fmtDate(a.due_date)}</td>
                      <td>
                        <Badge tone={TRAINING_TONE[a.effective_status]}>{TRAINING_LABEL[a.effective_status]}</Badge>
                        {a.completed_at && <div className="muted small">on {fmtDate(a.completed_at)}</div>}
                      </td>
                      <td className="actions">
                        {a.status !== 'completed' && <button className="btn btn-ok" onClick={() => mark(a.id, 'completed')}>Completed</button>}
                        {a.status === 'assigned' && <button className="btn btn-ghost danger" onClick={() => mark(a.id, 'missed')}>Missed</button>}
                        {a.status !== 'assigned' && <button className="btn btn-ghost" onClick={() => mark(a.id, 'assigned')}>Reopen</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === 'people' && overview && (
        <PeopleTab overview={overview} people={people ?? []} />
      )}

      {tab === 'courses' && (
        <>
          <div className="actions" style={{ marginBottom: 12 }}>
            <button className="btn btn-primary" onClick={() => setModal('course')}>New course</button>
          </div>
          {courses && courses.length === 0 && <Empty title="No courses yet">Create your first course.</Empty>}
          {courses && courses.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Course</th><th>Hours</th><th>Assigned</th><th>Completed</th><th /></tr></thead>
                <tbody>
                  {courses.map((c) => (
                    <tr key={c.id}>
                      <td>{c.title}{c.mandatory && <Badge tone="plain"> Mandatory</Badge>}<div className="muted small">{c.description}</div></td>
                      <td>{c.hours}</td><td>{c.assigned}</td><td>{c.completed}</td>
                      <td className="actions"><button className="btn btn-ghost danger" onClick={() => removeCourse(c)}>Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {modal === 'assign' && courses && departments && people && (
        <AssignForm courses={courses} departments={departments} people={people} onClose={() => setModal(null)}
          onSaved={(r) => { setModal(null); setFlash(`${r.created} assigned and notified${r.skipped ? `, ${r.skipped} skipped (already open)` : ''}.`); refresh() }} />
      )}
      {modal === 'course' && <CourseForm onClose={() => setModal(null)} onSaved={() => { setModal(null); refresh() }} />}
    </>
  )
}

function PeopleTab({ overview, people }) {
  const byId = Object.fromEntries(overview.people.map((p) => [p.employee_id, p]))
  const rows = people.map((p) => ({ p, o: byId[p.id] ?? { total: 0, completed: 0, outstanding: 0, hours_done: 0 } }))
    .sort((a, b) => b.o.outstanding - a.o.outstanding || fullName(a.p).localeCompare(fullName(b.p)))
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Person</th><th>Trainings done</th><th>Hours</th><th>Outstanding</th></tr></thead>
        <tbody>
          {rows.map(({ p, o }) => (
            <tr key={p.id}>
              <td><Person person={p} sub={p.department?.name ?? p.job_title} /></td>
              <td><strong>{o.completed}</strong> <span className="muted">of {o.total}</span></td>
              <td>{o.hours_done}</td>
              <td>{o.outstanding > 0 ? <Badge tone="bad">{o.outstanding}</Badge> : <span className="muted">0</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
