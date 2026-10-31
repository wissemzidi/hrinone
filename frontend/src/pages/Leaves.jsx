import { useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty, Modal, Notice, Person } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { LEAVE_TYPES, countDays, fmtRange, fullName, todayISO } from '../utils.js'

const TONES = { pending: 'warn', approved: 'ok', rejected: 'bad' }
const FILTERS = [
  ['', 'All'],
  ['pending', 'Pending'],
  ['approved', 'Approved'],
  ['rejected', 'Rejected'],
]

function LeaveForm({ onSaved, onClose }) {
  const { data: people } = useApi('/employees?status=active')
  const [form, setForm] = useState({
    employee_id: '',
    leave_type: 'vacation',
    start_date: todayISO(),
    end_date: todayISO(),
    reason: '',
  })
  const [error, setError] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await api.post('/leaves', { ...form, employee_id: Number(form.employee_id) })
      onSaved()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Modal title="New time-off request" onClose={onClose}>
      <form onSubmit={submit} className="form">
        <label>
          Person
          <select required value={form.employee_id} onChange={set('employee_id')}>
            <option value="">Choose a person</option>
            {(people ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {fullName(p)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Type
          <select value={form.leave_type} onChange={set('leave_type')}>
            {Object.entries(LEAVE_TYPES).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <div className="form-row">
          <label>
            First day
            <input required type="date" value={form.start_date} onChange={set('start_date')} />
          </label>
          <label>
            Last day
            <input required type="date" min={form.start_date} value={form.end_date} onChange={set('end_date')} />
          </label>
        </div>
        <label>
          Note (optional)
          <input maxLength={300} value={form.reason} onChange={set('reason')} />
        </label>
        {error && <p className="form-error">{error}</p>}
        <footer className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary">Submit request</button>
        </footer>
      </form>
    </Modal>
  )
}

export default function Leaves() {
  const [status, setStatus] = useState('')
  const [creating, setCreating] = useState(false)
  const { data: leaves, error, loading, reload } = useApi(`/leaves${status ? `?status=${status}` : ''}`)

  const decide = async (id, next) => {
    await api.patch(`/leaves/${id}`, { status: next })
    reload()
  }
  const remove = async (id) => {
    if (!window.confirm('Delete this request?')) return
    await api.del(`/leaves/${id}`)
    reload()
  }

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">Leave management</div>
          <h1>Time off</h1>
          <p className="muted">Review and record leave requests.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          New request
        </button>
      </header>

      <div className="tabs" role="tablist">
        {FILTERS.map(([value, label]) => (
          <button
            key={label}
            role="tab"
            aria-selected={status === value}
            className={`tab ${status === value ? 'active' : ''}`}
            onClick={() => setStatus(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <Notice error={error} onRetry={reload} />}
      {loading && <p className="muted">Loading…</p>}
      {leaves && leaves.length === 0 && (
        <Empty title="No requests here">Requests with this status will appear in this list.</Empty>
      )}
      {leaves && leaves.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Person</th>
                <th>Dates</th>
                <th>Type</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {leaves.map((l) => (
                <tr key={l.id}>
                  <td>
                    <Person person={l.employee} sub={l.reason || l.employee.job_title} />
                  </td>
                  <td>
                    {fmtRange(l.start_date, l.end_date)}
                    <div className="muted small">{countDays(l.start_date, l.end_date)} days</div>
                  </td>
                  <td>{LEAVE_TYPES[l.leave_type]}</td>
                  <td>
                    <Badge tone={TONES[l.status]}>{l.status[0].toUpperCase() + l.status.slice(1)}</Badge>
                  </td>
                  <td className="actions">
                    {l.status === 'pending' && (
                      <>
                        <button className="btn btn-ok" onClick={() => decide(l.id, 'approved')}>
                          Approve
                        </button>
                        <button className="btn" onClick={() => decide(l.id, 'rejected')}>
                          Reject
                        </button>
                      </>
                    )}
                    <button className="btn btn-ghost danger" onClick={() => remove(l.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {creating && (
        <LeaveForm
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            reload()
          }}
        />
      )}
    </>
  )
}
