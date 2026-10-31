import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { AttainmentChart, Sparkline, TrendBadge } from '../components/charts.jsx'
import { Badge, Empty, Modal, Notice } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { STATUS_LABEL, STATUS_TONE, VALUE_LABEL, VALUE_TONE, pct } from '../utils.js'

function TeamDetail({ team, onClose, goTo }) {
  const { data, error, loading } = useApi(`/analytics/teams/${team.id}`)
  const [ai, setAi] = useState(null)
  const [asking, setAsking] = useState(false)
  const [aiError, setAiError] = useState(null)

  useEffect(() => setAi(null), [team.id])

  const askAi = async () => {
    setAsking(true)
    setAiError(null)
    try {
      setAi(await api.get(`/analytics/teams/${team.id}?ai=true`))
    } catch (e) {
      setAiError(e.message)
    }
    setAsking(false)
  }

  const view = ai ?? data
  const jump = (action) => {
    if (action === 'training') goTo('training')
    if (action === 'people') goTo('employees')
    onClose()
  }

  return (
    <Modal title={`${team.name}: analysis`} onClose={onClose} wide>
      {error && <Notice error={error} />}
      {loading && <p className="muted">Analysing…</p>}
      {view && (
        <div className="detail">
          <div className="detail-top">
            <div>
              <p className="detail-headline">{view.headline}</p>
              <div className="row-inline" style={{ marginTop: 8 }}>
                <TrendBadge trend={view.summary.trend} delta={view.summary.delta} />
                <Badge tone={STATUS_TONE[view.summary.status]}>{STATUS_LABEL[view.summary.status]}</Badge>
                <Badge tone={VALUE_TONE[view.summary.value_added.verdict]}>
                  {VALUE_LABEL[view.summary.value_added.verdict]}
                </Badge>
              </div>
              <p className="muted small" style={{ marginTop: 8 }}>{view.summary.value_added.reason}</p>
            </div>
            <AttainmentChart series={view.series} />
          </div>

          <div className="driver-grid">
            <div className="driver">
              <span>Unplanned absence</span>
              <strong>{pct(view.absence_rate)}</strong>
              <small className="muted">last month {pct(view.absence_rate_prev)}</small>
            </div>
            <div className="driver">
              <span>Training completion</span>
              <strong>{pct(view.training_rate, 0)}</strong>
              <small className="muted">of assigned trainings</small>
            </div>
            <div className="driver">
              <span>People</span>
              <strong>{view.members.length}</strong>
              <small className="muted">active in this team</small>
            </div>
          </div>

          <section className="ai-box" aria-live="polite">
            <div className="ai-box-head">
              <strong>Written analysis</strong>
              <Badge tone={view.ai_powered ? 'ok' : 'plain'}>{view.ai_powered ? 'Written with an AI model' : 'Rule-based summary'}</Badge>
            </div>
            <p>{view.narrative}</p>
            {data?.ai_available ? (
              <button className="btn btn-primary" onClick={askAi} disabled={asking}>
                {asking ? 'Thinking…' : ai ? 'Ask again' : 'Write it with an AI model'}
              </button>
            ) : (
              <p className="muted small">
                Add an AI key (<code>GEMINI_API_KEY</code>) in <code>backend/.env</code> to get a written analysis from an AI model. The
                findings below always work offline.
              </p>
            )}
            {aiError && <p className="form-error">{aiError}</p>}
          </section>

          {view.causes.length === 0 ? (
            <div className="empty">
              <strong>{view.summary.status === 'on_track' ? 'Nothing to fix' : 'No clear cause in the data'}</strong>
              {view.strengths.length > 0 && (
                <ul className="plain-list">
                  {view.strengths.map((s) => <li key={s}>✓ {s}</li>)}
                </ul>
              )}
              {view.summary.status !== 'on_track' && (
                <p className="muted small">Absences, trainings and individual results look normal. Talk to the team lead about workload, targets and market factors.</p>
              )}
            </div>
          ) : (
            <>
              <h3>Likely causes, most important first</h3>
              {view.causes.map((c) => (
                <article key={c.key} className="cause">
                  <header>
                    <strong>{c.title}</strong>
                    <span className="sev" title="How strongly the data points to this cause">
                      <span className="bar"><span style={{ width: `${c.severity}%` }} /></span>
                      {c.severity}/100
                    </span>
                  </header>
                  <ul className="plain-list">
                    {c.evidence.map((e) => <li key={e}>{e}</li>)}
                  </ul>
                  <div className="solutions">
                    <div className="eyebrow">Suggested actions</div>
                    <ul>
                      {c.solutions.map((s) => (
                        <li key={s.text}>
                          <span>{s.text}</span>
                          {s.action && (
                            <button className="btn btn-ghost" onClick={() => jump(s.action)}>
                              {s.action === 'training' ? 'Open Training →' : 'Open People →'}
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                </article>
              ))}
            </>
          )}

          <h3>People in this team</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Person</th><th>Objectives reached</th><th>Absent days (month)</th><th>Trainings</th></tr>
              </thead>
              <tbody>
                {[...view.members].sort((a, b) => (a.perf ?? 101) - (b.perf ?? 101)).map((m) => (
                  <tr key={m.id}>
                    <td>{m.name}<div className="muted small">{m.title}</div></td>
                    <td>{m.perf == null ? '–' : <Badge tone={m.perf >= 85 ? 'ok' : m.perf >= 70 ? 'warn' : 'bad'}>{Math.round(m.perf)}%</Badge>}</td>
                    <td>{m.absence_days}</td>
                    <td>
                      {m.trainings_done}/{m.trainings_total}
                      {m.trainings_outstanding > 0 && <span className="bad-text small"> · {m.trainings_outstanding} outstanding</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted small note-human">
            These indicators help HR decide. They are not a verdict on any person: sick leave is a right, and every
            decision about people is taken by a human.
          </p>
        </div>
      )}
    </Modal>
  )
}

export default function Performance({ goTo }) {
  const { data: teams, error, loading, reload } = useApi('/analytics/teams')
  const [open, setOpen] = useState(null)

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">Team analytics</div>
          <h1>Team performance</h1>
          <p className="muted">
            Monthly result against target, with the likely causes when a team slips. Click a team for the full analysis.
          </p>
        </div>
      </header>

      {error && <Notice error={error} onRetry={reload} />}
      {loading && <p className="muted">Loading…</p>}
      {teams && teams.length === 0 && <Empty title="No performance data yet">Add monthly KPI figures per team to see them here.</Empty>}
      {teams && teams.length > 0 && (
        <div className="team-grid">
          {teams.map((t) => (
            <button key={t.id} className={`team-card status-${t.status}`} onClick={() => setOpen(t)}>
              <div className="team-card-head">
                <div>
                  <h2>{t.name}</h2>
                  <div className="muted small">{t.kpi} · {t.headcount} people</div>
                </div>
                <Badge tone={STATUS_TONE[t.status]}>{STATUS_LABEL[t.status]}</Badge>
              </div>
              <div className="team-card-main">
                <div>
                  <div className="big-number">{t.attainment.toFixed(0)}<span>%</span></div>
                  <TrendBadge trend={t.trend} delta={t.delta} />
                </div>
                <Sparkline values={t.series.map((s) => s.attainment)} />
              </div>
              <div className="team-card-foot">
                <Badge tone={VALUE_TONE[t.value_added.verdict]}>{VALUE_LABEL[t.value_added.verdict]}</Badge>
                <span className="muted small">
                  Absence {pct(t.absence_rate)} · Training {pct(t.training_rate, 0)}
                </span>
              </div>
              {t.top_cause && <div className="team-card-cause">⚠ Main signal: {t.top_cause}</div>}
            </button>
          ))}
        </div>
      )}
      {open && <TeamDetail team={open} goTo={goTo} onClose={() => setOpen(null)} />}
    </>
  )
}
