import { api } from '../api.js'
import { Badge, Empty, Notice, OrbArt, Person } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { LEAVE_TYPES, countDays, fmtDate, fmtRange } from '../utils.js'

export default function Dashboard({ goTo }) {
  const { data, error, loading, reload } = useApi('/stats')

  if (error) return <Notice error={error} onRetry={reload} />
  if (loading) return <p className="muted">Loading…</p>

  const decide = async (id, status) => {
    await api.patch(`/leaves/${id}`, { status })
    reload()
  }

  const maxCount = Math.max(1, ...data.by_department.map((d) => d.count))

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">
            <span className="pulse" /> Your team today
          </div>
          <h1>Who's out today</h1>
          <p className="muted">
            {data.out_today.length === 0
              ? 'Everyone is in.'
              : `${data.out_today.length} of ${data.active_employees} active people are away.`}
          </p>
        </div>
      </header>

      <section className="hero-banner">
        <div className="hero-content">
          <h2>
            Keep time off clear,
            <br />
            <em>and every decision yours.</em>
          </h2>
          <p>See who is away, approve requests and keep your team's calendar in order.</p>
          <button className="btn btn-light" onClick={() => goTo('leaves')}>
            Review time off →
          </button>
        </div>
        <OrbArt />
        <div className="hero-grid" />
      </section>

      <div className="stats-grid">
        <article className="stat-card">
          <span className="stat-icon cyan" aria-hidden="true">♙</span>
          <div className="stat-value">{data.active_employees}</div>
          <div className="stat-label">Active people</div>
          <small className="stat-note">Currently on the team</small>
        </article>
        <article className="stat-card">
          <span className="stat-icon blue" aria-hidden="true">▦</span>
          <div className="stat-value">{data.out_today.length}</div>
          <div className="stat-label">Away today</div>
          <small className="stat-note">Approved time off</small>
        </article>
        <article className="stat-card">
          <span className="stat-icon violet" aria-hidden="true">◷</span>
          <div className="stat-value">{data.pending.length}</div>
          <div className="stat-label">Waiting for you</div>
          <small className="stat-note">Requests to decide</small>
        </article>
        <article className="stat-card">
          <span className="stat-icon green" aria-hidden="true">◫</span>
          <div className="stat-value">{data.by_department.length}</div>
          <div className="stat-label">Departments</div>
          <small className="stat-note">Across the company</small>
        </article>
      </div>

      <section className="panel" style={{ marginTop: 16 }}>
        <div className="panel-head">
          <h2>Away today</h2>
        </div>
        {data.out_today.length === 0 ? (
          <Empty title="No one is away">Approved time off that covers today will show up here.</Empty>
        ) : (
          <ul className="list">
            {data.out_today.map((l) => (
              <li key={l.id} className="row">
                <Person person={l.employee} sub={`${LEAVE_TYPES[l.leave_type]} · back after ${fmtDate(l.end_date)}`} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="grid-2">
        <section className="panel">
          <div className="panel-head">
            <h2>Waiting for your decision</h2>
            <button className="btn btn-ghost" onClick={() => goTo('leaves')}>
              See all time off
            </button>
          </div>
          {data.pending.length === 0 ? (
            <Empty title="Nothing to review">New requests will appear here.</Empty>
          ) : (
            <ul className="list">
              {data.pending.map((l) => (
                <li key={l.id} className="row">
                  <Person
                    person={l.employee}
                    sub={`${fmtRange(l.start_date, l.end_date)} (${countDays(l.start_date, l.end_date)}d)`}
                  />
                  <div className="actions">
                    <button className="btn btn-ok" onClick={() => decide(l.id, 'approved')}>
                      Approve
                    </button>
                    <button className="btn" onClick={() => decide(l.id, 'rejected')}>
                      Reject
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Active people by department</h2>
            <Badge tone="plain">{data.active_employees} active</Badge>
          </div>
          <ul className="bars">
            {data.by_department.map((d) => (
              <li key={d.name}>
                <span>{d.name}</span>
                <span className="bar">
                  <span style={{ width: `${(d.count / maxCount) * 100}%` }} />
                </span>
                <strong>{d.count}</strong>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  )
}
