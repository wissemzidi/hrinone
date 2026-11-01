import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Security() {
  const [events, setEvents] = useState([])
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    setLoading(true); setError('')
    try {
      const [e, s] = await Promise.all([api.get('/auth/security/events?limit_count=200'), api.get('/auth/security/sessions')])
      setEvents(e); setSessions(s)
    } catch (err) { setError(err.message || 'Could not load security data') }
    finally { setLoading(false) }
  }
  useEffect(() => { refresh() }, [])

  const revoke = async (id) => {
    if (!window.confirm('Revoke this session immediately?')) return
    try { await api.del(`/auth/security/sessions/${id}`); await refresh() }
    catch (err) { setError(err.message || 'Could not revoke session') }
  }

  const date = (value) => value ? new Date(value).toLocaleString() : '—'
  return <div className="page">
    <div className="page-head"><div><p className="eyebrow">ADMINISTRATION</p><h1>Security center</h1><p className="muted">Login activity, active sessions and security audit trail.</p></div><button className="btn" onClick={refresh}>Refresh</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="panel" style={{ marginBottom: 24 }}>
      <h2>Active sessions <span className="muted">({sessions.length})</span></h2>
      {loading ? <p className="muted">Loading…</p> : sessions.length === 0 ? <p className="muted">No active sessions.</p> : <div className="table-wrap"><table><thead><tr><th>User</th><th>IP address</th><th>Started</th><th>Last activity</th><th>Device</th><th></th></tr></thead><tbody>{sessions.map(s => <tr key={s.id}><td>{s.email}</td><td>{s.ip_address}</td><td>{date(s.created_at)}</td><td>{date(s.last_seen_at)}</td><td title={s.user_agent}>{(s.user_agent || 'Unknown').slice(0, 55)}</td><td><button className="btn btn-ghost" onClick={() => revoke(s.id)}>Revoke</button></td></tr>)}</tbody></table></div>}
    </section>
    <section className="panel">
      <h2>Security events <span className="muted">({events.length} latest)</span></h2>
      <p className="muted small">Tracks successful/failed logins and authenticated write requests. Passwords, tokens and request bodies are never recorded.</p>
      {loading ? <p className="muted">Loading…</p> : events.length === 0 ? <p className="muted">No security events recorded yet.</p> : <div className="table-wrap"><table><thead><tr><th>Time</th><th>Event</th><th>Account</th><th>IP</th><th>Request</th><th>Status</th></tr></thead><tbody>{events.map(e => <tr key={e.id}><td>{date(e.occurred_at)}</td><td><strong>{e.event_type}</strong></td><td>{e.email || (e.user_id ? `User #${e.user_id}` : 'Unknown')}</td><td>{e.ip_address}</td><td>{e.method} {e.path}</td><td>{e.status_code || '—'}</td></tr>)}</tbody></table></div>}
    </section>
  </div>
}
