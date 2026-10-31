import { useApi } from '../hooks.js'
import { Badge } from './ui.jsx'
import { AttainmentChart, TrendBadge } from './charts.jsx'
import { STATUS_LABEL, STATUS_TONE, pct } from '../utils.js'

/** "State of the company" block for the dashboard. */
export default function CompanyHealth({ goTo }) {
  const { data: c, error } = useApi('/analytics/company')
  if (error) return null
  if (!c) return <p className="muted">Loading company health…</p>
  if (c.attainment == null) return null

  const absDelta = c.absence_rate - c.absence_rate_prev
  return (
    <section className="panel company" aria-label="Company health">
      <div className="panel-head">
        <div>
          <div className="eyebrow">State of the company</div>
          <h2>Company performance this month</h2>
        </div>
        <button className="btn btn-ghost" onClick={() => goTo('performance')}>
          Analyse teams →
        </button>
      </div>

      <div className="company-grid">
        <div>
          <div className="big-number">
            {c.attainment.toFixed(0)}
            <span>% of target</span>
          </div>
          <div className="row-inline">
            <TrendBadge trend={c.trend} delta={c.delta} />
            <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABEL[c.status]}</Badge>
          </div>
          <p className="muted small" style={{ marginTop: 10 }}>
            Average of all teams' targets. {c.teams_on_track} of {c.teams_total} teams on track
            {c.teams_off_track > 0 && `, ${c.teams_off_track} off track`}.
          </p>
        </div>
        <AttainmentChart series={c.series} height={140} />
        <ul className="mini-kpis">
          <li>
            <span>Unplanned absence</span>
            <strong>{pct(c.absence_rate)}</strong>
            <small className={absDelta > 0.002 ? 'bad-text' : 'muted'}>
              {absDelta > 0.002 ? '▲' : absDelta < -0.002 ? '▼' : '►'} vs {pct(c.absence_rate_prev)} last month
            </small>
          </li>
          <li>
            <span>Training completion</span>
            <strong>{pct(c.training_rate, 0)}</strong>
            <small className="muted">of assigned trainings</small>
          </li>
          <li>
            <span>Waiting for HR</span>
            <strong>{c.pending_leaves + c.pending_documents + c.open_questions + c.new_applications}</strong>
            <small className="muted">
              {c.pending_leaves} leave · {c.pending_documents} docs · {c.open_questions} questions · {c.new_applications} CVs
            </small>
          </li>
        </ul>
      </div>

      <ul className="team-strip">
        {c.teams.map((t) => (
          <li key={t.id}>
            <button className="team-chip" onClick={() => goTo('performance')}>
              <span>{t.name}</span>
              <strong>{t.attainment.toFixed(0)}%</strong>
              <TrendBadge trend={t.trend} delta={t.delta} />
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
