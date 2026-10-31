import { useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty, Modal, Notice, Person } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { fmtDate, fullName, todayISO } from '../utils.js'

const BLANK = {
  first_name: '',
  last_name: '',
  email: '',
  job_title: '',
  hire_date: todayISO(),
  status: 'active',
  department_id: '',
  password: '',
}

function EmployeeForm({ employee, departments, onSaved, onClose }) {
  const [form, setForm] = useState(
    employee ? { ...employee, department_id: employee.department_id ?? '' } : BLANK,
  )
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    const body = {
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      job_title: form.job_title,
      hire_date: form.hire_date,
      status: form.status,
      department_id: form.department_id === '' ? null : Number(form.department_id),
      ...(employee ? {} : { password: form.password }),
    }
    try {
      if (employee) await api.put(`/employees/${employee.id}`, body)
      else await api.post('/employees', body)
      onSaved()
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <Modal title={employee ? 'Edit person' : 'Add person'} onClose={onClose}>
      <form onSubmit={submit} className="form">
        <div className="form-row">
          <label>
            First name
            <input required value={form.first_name} onChange={set('first_name')} />
          </label>
          <label>
            Last name
            <input required value={form.last_name} onChange={set('last_name')} />
          </label>
        </div>
        <label>
          Work email
          <input required type="email" value={form.email} onChange={set('email')} />
        </label>
        {!employee && (
          <label>
            Temporary password (they use it to sign in)
            <input required minLength={6} type="text" value={form.password} onChange={set('password')} />
          </label>
        )}
        <label>
          Job title
          <input required value={form.job_title} onChange={set('job_title')} />
        </label>
        <div className="form-row">
          <label>
            Department
            <select value={form.department_id} onChange={set('department_id')}>
              <option value="">No department</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Start date
            <input required type="date" value={form.hire_date} onChange={set('hire_date')} />
          </label>
        </div>
        <label>
          Status
          <select value={form.status} onChange={set('status')}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
        {error && <p className="form-error">{error}</p>}
        <footer className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save person'}
          </button>
        </footer>
      </form>
    </Modal>
  )
}

export default function Employees() {
  const [search, setSearch] = useState('')
  const [dept, setDept] = useState('')
  const [editing, setEditing] = useState(null) // null | 'new' | employee

  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (dept) params.set('department_id', dept)
  const { data: people, error, loading, reload } = useApi(`/employees?${params}`)
  const { data: departments } = useApi('/departments')
  const { data: training } = useApi('/training/overview')
  const trainingById = Object.fromEntries((training?.people ?? []).map((t) => [t.employee_id, t]))

  const remove = async (p) => {
    if (!window.confirm(`Remove ${fullName(p)}? Their time-off history is deleted too.`)) return
    await api.del(`/employees/${p.id}`)
    reload()
  }

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">Team directory</div>
          <h1>People</h1>
          <p className="muted">{people ? `${people.length} shown` : ' '}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setEditing('new')}>
          Add person
        </button>
      </header>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search by name, email or title"
          aria-label="Search people"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select aria-label="Filter by department" value={dept} onChange={(e) => setDept(e.target.value)}>
          <option value="">All departments</option>
          {(departments ?? []).map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>

      {error && <Notice error={error} onRetry={reload} />}
      {loading && <p className="muted">Loading…</p>}
      {people && people.length === 0 && (
        <Empty title="No one matches">Try a different search, or add a new person.</Empty>
      )}
      {people && people.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Person</th>
                <th>Department</th>
                <th>Started</th>
                <th>Trainings done</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {people.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Person person={p} sub={`${p.job_title} · ${p.email}`} />
                  </td>
                  <td>{p.department?.name ?? <span className="muted">None</span>}</td>
                  <td>{fmtDate(p.hire_date)}</td>
                  <td>
                    {trainingById[p.id] ? (
                      <>
                        <strong>{trainingById[p.id].completed}</strong>
                        <span className="muted"> of {trainingById[p.id].total}</span>
                        {trainingById[p.id].outstanding > 0 && <Badge tone="bad"> {trainingById[p.id].outstanding} late</Badge>}
                      </>
                    ) : (
                      <span className="muted">None</span>
                    )}
                  </td>
                  <td>
                    <Badge tone={p.status === 'active' ? 'ok' : 'plain'}>
                      {p.status === 'active' ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="actions">
                    <button className="btn btn-ghost" onClick={() => setEditing(p)}>
                      Edit
                    </button>
                    <button className="btn btn-ghost danger" onClick={() => remove(p)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <EmployeeForm
          employee={editing === 'new' ? null : editing}
          departments={departments ?? []}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            reload()
          }}
        />
      )}
    </>
  )
}
