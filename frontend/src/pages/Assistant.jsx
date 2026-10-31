import { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { downloadBlob, fmtDate } from '../utils.js'

const SUGGESTIONS = [
  'How many vacation days do I have left?',
  'When are salaries paid?',
  'Do I need a medical certificate when I am sick?',
  'How many trainings have I completed?',
  'I need a work certificate',
]

const DOCS = [
  { type: 'work_certificate', label: 'Work certificate', hint: 'Instant' },
  { type: 'leave_summary', label: 'Leave summary', hint: 'Instant' },
  { type: 'training_record', label: 'Training record', hint: 'Instant' },
  { type: 'salary_certificate', label: 'Salary certificate', hint: 'HR approves' },
]

const STATUS = { ready: ['ok', 'Ready'], pending: ['warn', 'Waiting for HR'], rejected: ['bad', 'Declined'] }

export default function Assistant({ user }) {
  const [messages, setMessages] = useState([
    { role: 'bot', text: `Hi ${user.employee?.first_name}! Ask me about leave, pay, policies or your trainings, or ask for a document. I only use company documents and your own file.` },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef(null)
  const { data: docs, reload: reloadDocs } = useApi('/documents/mine')
  const { data: questions, reload: reloadQuestions } = useApi('/assistant/mine')

  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), [messages])

  const ask = async (text) => {
    const q = text.trim()
    if (!q || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: q }])
    setBusy(true)
    try {
      const r = await api.post('/assistant/ask', { question: q })
      setMessages((m) => [...m, { role: 'bot', text: r.answer, sources: r.sources, request: r.request, escalate: r.can_escalate ? q : null, ai: r.ai_powered }])
      if (r.request) reloadDocs()
    } catch (e) {
      setMessages((m) => [...m, { role: 'bot', text: e.message, error: true }])
    }
    setBusy(false)
  }

  const escalate = async (q, idx) => {
    try {
      await api.post('/assistant/escalate', { question: q })
      setMessages((m) => m.map((x, i) => (i === idx ? { ...x, escalate: null } : x)).concat({ role: 'bot', text: 'Sent to HR. You will get a notification when they answer.' }))
      reloadQuestions()
    } catch (e) {
      setMessages((m) => [...m, { role: 'bot', text: e.message, error: true }])
    }
  }

  const requestDoc = async (type) => {
    try {
      const r = await api.post('/documents', { doc_type: type })
      setMessages((m) => [...m, { role: 'bot', text: r.status === 'ready' ? `Your ${r.label.toLowerCase()} is ready.` : `Your ${r.label.toLowerCase()} request is with HR for approval.`, request: { id: r.id, status: r.status, label: r.label } }])
      reloadDocs()
    } catch (e) {
      setMessages((m) => [...m, { role: 'bot', text: e.message, error: true }])
    }
  }

  const download = async (d) => {
    const blob = await api.blob(`/documents/${d.id}/download`)
    downloadBlob(blob, `${d.doc_type}.docx`)
  }

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">HR assistant</div>
          <h1>Ask, don't wait</h1>
          <p className="muted">Get answers and documents instantly. If I can't help, I pass your question to HR.</p>
        </div>
      </header>

      <div className="assistant-grid">
        <section className="panel chat" aria-label="Chat with the HR assistant">
          <div className="chat-log" role="log" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`bubble ${m.role} ${m.error ? 'error' : ''}`}>
                <p>{m.text}</p>
                {m.sources?.length > 0 && <div className="muted tiny">Source: {m.sources.map((s) => s.title).join(', ')}</div>}
                {m.request?.status === 'ready' && (
                  <button className="btn btn-ok" onClick={() => download(m.request)}>Download {m.request.label.toLowerCase()}</button>
                )}
                {m.escalate && <button className="btn" onClick={() => escalate(m.escalate, i)}>Send to HR</button>}
              </div>
            ))}
            {busy && <div className="bubble bot"><p className="muted">Thinking…</p></div>}
            <div ref={end} />
          </div>
          <div className="chips">
            {SUGGESTIONS.map((s) => <button key={s} className="chip" onClick={() => ask(s)}>{s}</button>)}
          </div>
          <form className="chat-input" onSubmit={(e) => { e.preventDefault(); ask(input) }}>
            <input value={input} maxLength={500} onChange={(e) => setInput(e.target.value)} placeholder="Ask about leave, pay, policies, trainings…" aria-label="Your question" />
            <button className="btn btn-primary" disabled={busy || !input.trim()}>Send</button>
          </form>
        </section>

        <aside className="side-stack">
          <section className="panel">
            <div className="panel-head"><h2>Request a document</h2></div>
            <ul className="doc-buttons">
              {DOCS.map((d) => (
                <li key={d.type}>
                  <button className="btn" onClick={() => requestDoc(d.type)}>
                    <span>{d.label}</span><small className="muted">{d.hint}</small>
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel">
            <div className="panel-head"><h2>My documents</h2></div>
            {docs && docs.length === 0 && <p className="muted small">Nothing requested yet.</p>}
            <ul className="list">
              {(docs ?? []).slice(0, 8).map((d) => (
                <li key={d.id} className="row">
                  <div>
                    <div className="person-name">{d.label}</div>
                    <div className="muted small">{fmtDate(d.created_at.slice(0, 10))}</div>
                    {d.status === 'rejected' && d.note && <div className="muted small">“{d.note}”</div>}
                  </div>
                  {d.status === 'ready' ? (
                    <button className="btn btn-ok" onClick={() => download(d)}>Download</button>
                  ) : (
                    <Badge tone={STATUS[d.status][0]}>{STATUS[d.status][1]}</Badge>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <section className="panel">
            <div className="panel-head"><h2>Questions sent to HR</h2></div>
            {questions && questions.length === 0 && <Empty title="None">Unanswered questions you forward show up here.</Empty>}
            <ul className="list">
              {(questions ?? []).map((q) => (
                <li key={q.id} className="qa">
                  <div className="person-name">{q.question}</div>
                  {q.status === 'answered' ? <div className="small">HR: {q.answer}</div> : <Badge tone="warn">Waiting for HR</Badge>}
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </>
  )
}
