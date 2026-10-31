import { useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty, Modal, Notice } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { LEAVE_TYPES, countDays, fmtRange, todayISO } from '../utils.js'

const TONES = { pending: 'warn', approved: 'ok', rejected: 'bad' }

function RequestForm({ onSaved, onClose }) {
  const [form, setForm] = useState({ leave_type: 'vacation', start_date: todayISO(), end_date: todayISO(), reason: '' })
  const [error, setError] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await api.post('/leaves', form)
      onSaved()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Modal title="Request time off" onClose={onClose}>
      <form onSubmit={submit} className="form">
        <label>
          Type
          <select value={form.leave_type} onChange={set('leave_type')}>
            {Object.entries(LEAVE_TYPES).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
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
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary">Send request</button>
        </footer>
      </form>
    </Modal>
  )
}

export default function MyLeaves({ user }) {
  const { data: leaves, error, loading, reload } = useApi('/leaves')
  const [creating, setCreating] = useState(false)

  const cancel = async (id) => {
    if (!window.confirm('Cancel this request?')) return
    await api.del(`/leaves/${id}`)
    reload()
  }

  const approvedDays = (leaves ?? [])
    .filter((l) => l.status === 'approved')
    .reduce((sum, l) => sum + countDays(l.start_date, l.end_date), 0)
  const pending = (leaves ?? []).filter((l) => l.status === 'pending').length

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">Your time off</div>
          <h1>Hi, {user.employee?.first_name}</h1>
          <p className="muted">
            {leaves ? `${approvedDays} approved days off · ${pending} waiting for approval` : ' '}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>Request time off</button>
      </header>

      {error && <Notice error={error} onRetry={reload} />}
      {loading && <p className="muted">Loading…</p>}
      {leaves && leaves.length === 0 && (
        <Empty title="No requests yet">Request vacation, sick days or personal leave and track the answer here.</Empty>
      )}
      {leaves && leaves.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Dates</th><th>Type</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {leaves.map((l) => (
                <tr key={l.id}>
                  <td>
                    {fmtRange(l.start_date, l.end_date)}
                    <div className="muted small">{countDays(l.start_date, l.end_date)} days{l.reason ? ` · ${l.reason}` : ''}</div>
                  </td>
                  <td>{LEAVE_TYPES[l.leave_type]}</td>
                  <td><Badge tone={TONES[l.status]}>{l.status[0].toUpperCase() + l.status.slice(1)}</Badge></td>
                  <td className="actions">
                    {l.status === 'pending' && (
                      <button className="btn btn-ghost danger" onClick={() => cancel(l.id)}>Cancel</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {creating && (
        <RequestForm
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
