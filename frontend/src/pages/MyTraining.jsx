import { Badge, Empty, Notice } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { TRAINING_LABEL, TRAINING_TONE, fmtDate } from '../utils.js'

export default function MyTraining({ user }) {
  const { data, error, loading, reload } = useApi('/training/mine')
  const s = data?.summary

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">Your learning</div>
          <h1>My training</h1>
          <p className="muted">
            {s ? `${s.completed} completed · ${s.hours_done} hours · ${s.outstanding} to catch up` : ' '}
          </p>
        </div>
      </header>

      {error && <Notice error={error} onRetry={reload} />}
      {loading && <p className="muted">Loading…</p>}
      {s && (
        <div className="stats-grid">
          <article className="stat-card"><div className="stat-value">{s.completed}</div><div className="stat-label">Completed</div><small className="stat-note">{s.hours_done} hours of learning</small></article>
          <article className="stat-card"><div className="stat-value">{s.upcoming}</div><div className="stat-label">Upcoming</div><small className="stat-note">Still before the due date</small></article>
          <article className="stat-card"><div className="stat-value">{s.outstanding}</div><div className="stat-label">To catch up</div><small className="stat-note">Overdue or missed</small></article>
          <article className="stat-card"><div className="stat-value">{s.total}</div><div className="stat-label">Assigned in total</div></article>
        </div>
      )}
      {data && data.items.length === 0 && (
        <div style={{ marginTop: 16 }}><Empty title="No trainings yet">When HR programs a training for you, it shows up here and you get a notification, {user.employee?.first_name}.</Empty></div>
      )}
      {data && data.items.length > 0 && (
        <div className="table-wrap" style={{ marginTop: 16 }}>
          <table>
            <thead><tr><th>Course</th><th>Due</th><th>Status</th></tr></thead>
            <tbody>
              {data.items.map((a) => (
                <tr key={a.id}>
                  <td>{a.course.title}{a.course.mandatory && <Badge tone="plain"> Mandatory</Badge>}<div className="muted small">{a.course.hours} h</div></td>
                  <td>{fmtDate(a.due_date)}</td>
                  <td>
                    <Badge tone={TRAINING_TONE[a.effective_status]}>{TRAINING_LABEL[a.effective_status]}</Badge>
                    {a.completed_at && <div className="muted small">on {fmtDate(a.completed_at)}</div>}
                    {['overdue', 'missed'].includes(a.effective_status) && <div className="muted small">Ask the assistant or HR to book a new slot.</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
