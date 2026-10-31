import { useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty, Modal, Notice, Person } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { fmtDate } from '../utils.js'

function DocumentsTab() {
  const { data, error, reload } = useApi('/documents')
  const [salary, setSalary] = useState({})
  const [err, setErr] = useState(null)

  const decide = async (r, status) => {
    setErr(null)
    try {
      const note = status === 'rejected' ? window.prompt('Reason for declining (shown to the employee)') ?? '' : ''
      await api.patch(`/documents/${r.id}`, { status, salary: salary[r.id] ?? '', note })
      reload()
    } catch (e) {
      setErr(e.message)
    }
  }
  const pending = (data ?? []).filter((r) => r.status === 'pending')
  const done = (data ?? []).filter((r) => r.status !== 'pending')

  return (
    <>
      <p className="muted" style={{ marginBottom: 12 }}>
        Work certificates, leave summaries and training records are produced instantly from HR records. Salary
        certificates wait here for your approval.
      </p>
      {error && <Notice error={error} onRetry={reload} />}
      {err && <p className="form-error">{err}</p>}
      <h3>Waiting for approval</h3>
      {data && pending.length === 0 && <Empty title="Nothing to approve">Salary certificate requests appear here.</Empty>}
      <ul className="list panel">
        {pending.map((r) => (
          <li key={r.id} className="row wrap">
            <Person person={r.employee} sub={`${r.label} · ${fmtDate(r.created_at.slice(0, 10))}`} />
            <div className="actions">
              {r.doc_type === 'salary_certificate' && (
                <input aria-label="Salary to print" placeholder="e.g. 2,400 TND gross / month" value={salary[r.id] ?? ''}
                  onChange={(e) => setSalary({ ...salary, [r.id]: e.target.value })} style={{ width: 230 }} />
              )}
              <button className="btn btn-ok" onClick={() => decide(r, 'approved')}>Approve</button>
              <button className="btn" onClick={() => decide(r, 'rejected')}>Decline</button>
            </div>
          </li>
        ))}
      </ul>
      <h3>History</h3>
      {done.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Person</th><th>Document</th><th>Date</th><th>Status</th></tr></thead>
            <tbody>
              {done.map((r) => (
                <tr key={r.id}>
                  <td><Person person={r.employee} /></td><td>{r.label}</td><td>{fmtDate(r.created_at.slice(0, 10))}</td>
                  <td><Badge tone={r.status === 'ready' ? 'ok' : 'bad'}>{r.status === 'ready' ? 'Issued' : 'Declined'}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

function QuestionsTab() {
  const { data, error, reload } = useApi('/assistant/questions')
  const [drafts, setDrafts] = useState({})
  const send = async (q) => {
    if (!drafts[q.id]?.trim()) return
    await api.patch(`/assistant/questions/${q.id}`, { answer: drafts[q.id] })
    reload()
  }
  return (
    <>
      <p className="muted" style={{ marginBottom: 12 }}>
        These are questions the assistant could not answer from your documents. Answer them here, then consider adding the
        answer to the knowledge base so nobody has to ask twice.
      </p>
      {error && <Notice error={error} onRetry={reload} />}
      {data && data.length === 0 && <Empty title="No questions">Questions employees forward to HR show up here.</Empty>}
      <ul className="list panel">
        {(data ?? []).map((q) => (
          <li key={q.id} className="qa">
            <Person person={q.employee} sub={fmtDate(q.created_at.slice(0, 10))} />
            <p style={{ margin: '8px 0' }}>{q.question}</p>
            {q.status === 'answered' ? (
              <div className="small"><Badge tone="ok">Answered</Badge> {q.answer}</div>
            ) : (
              <div className="actions" style={{ justifyContent: 'stretch' }}>
                <input aria-label="Your answer" placeholder="Type your answer" value={drafts[q.id] ?? ''} onChange={(e) => setDrafts({ ...drafts, [q.id]: e.target.value })} />
                <button className="btn btn-primary" onClick={() => send(q)}>Reply</button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </>
  )
}

function DocForm({ doc, onSaved, onClose }) {
  const [form, setForm] = useState(doc ?? { title: '', category: 'General', keywords: '', content: '' })
  const [error, setError] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault()
    const body = { title: form.title, category: form.category, keywords: form.keywords, content: form.content }
    try {
      if (doc) await api.put(`/knowledge/${doc.id}`, body)
      else await api.post('/knowledge', body)
      onSaved()
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <Modal title={doc ? 'Edit document' : 'Add company document'} onClose={onClose} wide>
      <form className="form" onSubmit={submit}>
        <div className="form-row">
          <label>Title<input required maxLength={120} value={form.title} onChange={set('title')} /></label>
          <label>Category<input maxLength={60} value={form.category} onChange={set('category')} /></label>
        </div>
        <label>
          Search keywords (synonyms, French, darija)
          <input maxLength={300} value={form.keywords} onChange={set('keywords')} placeholder="congé vacances holiday" />
        </label>
        <label>
          Content (one rule per line works best)
          <textarea required rows={8} maxLength={6000} value={form.content} onChange={set('content')} />
        </label>
        {error && <p className="form-error">{error}</p>}
        <footer className="form-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary">Save</button>
        </footer>
      </form>
    </Modal>
  )
}

function KnowledgeTab() {
  const { data, error, reload } = useApi('/knowledge')
  const [editing, setEditing] = useState(null)
  const remove = async (d) => {
    if (!window.confirm(`Delete “${d.title}”?`)) return
    await api.del(`/knowledge/${d.id}`)
    reload()
  }
  return (
    <>
      <div className="page-head" style={{ marginBottom: 12 }}>
        <p className="muted">The assistant answers only from these documents. Keep them current: the demo ones are samples.</p>
        <button className="btn btn-primary" onClick={() => setEditing('new')}>Add document</button>
      </div>
      {error && <Notice error={error} onRetry={reload} />}
      <div className="table-wrap">
        <table>
          <thead><tr><th>Document</th><th>Category</th><th /></tr></thead>
          <tbody>
            {(data ?? []).map((d) => (
              <tr key={d.id}>
                <td><strong>{d.title}</strong><div className="muted small">{d.content.slice(0, 110)}{d.content.length > 110 ? '…' : ''}</div></td>
                <td>{d.category}</td>
                <td className="actions">
                  <button className="btn btn-ghost" onClick={() => setEditing(d)}>Edit</button>
                  <button className="btn btn-ghost danger" onClick={() => remove(d)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && <DocForm doc={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload() }} />}
    </>
  )
}

export default function Requests() {
  const [tab, setTab] = useState('documents')
  const { data: docs } = useApi('/documents?status=pending')
  const { data: qs } = useApi('/assistant/questions')
  const openQs = (qs ?? []).filter((q) => q.status === 'open').length
  const tabs = [
    ['documents', 'Documents', docs?.length ?? 0],
    ['questions', 'Employee questions', openQs],
    ['knowledge', 'Knowledge base', 0],
  ]
  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">HR assistant</div>
          <h1>Requests</h1>
          <p className="muted">What the assistant could not decide alone, and the documents it answers from.</p>
        </div>
      </header>
      <div className="tabs" role="tablist">
        {tabs.map(([id, label, n]) => (
          <button key={id} role="tab" aria-selected={tab === id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>
            {label}{n > 0 && <span className="tab-count">{n}</span>}
          </button>
        ))}
      </div>
      {tab === 'documents' && <DocumentsTab />}
      {tab === 'questions' && <QuestionsTab />}
      {tab === 'knowledge' && <KnowledgeTab />}
    </>
  )
}
