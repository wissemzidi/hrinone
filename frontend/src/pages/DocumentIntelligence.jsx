import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function DocumentIntelligence() {
  const [docs, setDocs] = useState([])
  const [file, setFile] = useState(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [summary, setSummary] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [compareA, setCompareA] = useState('')
  const [compareB, setCompareB] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = async () => {
    try { setDocs(await api.get('/document-intelligence/documents')) }
    catch (e) { setError(e.message) }
  }
  useEffect(() => { load() }, [])

  const run = async (key, action) => {
    setBusy(key); setError(''); setNotice('')
    try { await action() } catch (e) { setError(e.message || 'Something went wrong.') }
    finally { setBusy('') }
  }

  const upload = (e) => {
    e.preventDefault()
    const formElement = e.currentTarget
    if (!file) { setError('Choose a PDF, DOCX or TXT file first.'); return }
    run('upload', async () => {
      const form = new FormData()
      form.append('file', file)
      const result = await api.post('/document-intelligence/upload', form)
      setNotice(`${result.title} uploaded and indexed (${result.characters.toLocaleString()} characters).`)
      setFile(null)
      formElement.reset()
      await load()
    })
  }

  const ask = (e) => {
    e.preventDefault()
    run('ask', async () => setAnswer(await api.post('/document-intelligence/ask', { question })))
  }

  const summarize = (id) => run(`summary-${id}`, async () => {
    setSummary(await api.post(`/document-intelligence/summarize/${id}`, {}))
  })

  const compare = (e) => {
    e.preventDefault()
    run('compare', async () => setComparison(await api.post('/document-intelligence/compare', { document_a: Number(compareA), document_b: Number(compareB) })))
  }

  const remove = (doc) => {
    if (!window.confirm(`Delete “${doc.title}” from the knowledge base?`)) return
    run(`delete-${doc.id}`, async () => { await api.del(`/document-intelligence/documents/${doc.id}`); setNotice('Document deleted.'); await load() })
  }

  return <>
    <header className="page-head">
      <div><div className="eyebrow">AI workspace · RAG</div><h1>Document intelligence</h1><p className="muted">Upload HR policies, ask grounded questions, summarize documents, and compare versions.</p></div>
    </header>

    {notice && <div className="flash" role="status" style={{ margin: '0 0 16px' }}>{notice}</div>}
    {error && <div className="form-error" role="alert" style={{ margin: '0 0 16px' }}>{error}</div>}

    <div className="grid-2" style={{ alignItems: 'start' }}>
      <section className="panel" style={{ padding: 22 }}>
        <div className="eyebrow">01 · Knowledge base</div><h2>Upload a document</h2>
        <p className="muted">PDF, Word or text · max 5 MB. Text-based documents only; scanned PDFs need OCR.</p>
        <form className="form" onSubmit={upload}>
          <label>Choose file<input type="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" onChange={e => setFile(e.target.files?.[0] || null)} /></label>
          <button type="submit" className="btn btn-primary" disabled={busy === 'upload'}>{busy === 'upload' ? 'Reading document…' : 'Upload & index'}</button>
        </form>
        <div style={{ marginTop: 24 }}><h3>Indexed documents <span className="badge badge-plain">{docs.length}</span></h3>
          {docs.length === 0 ? <p className="muted">No documents yet. Upload a policy to get started.</p> : <div>
            {docs.map(d => <div key={d.id} className="row" style={{ alignItems: 'flex-start', gap: 12 }}>
              <div style={{ minWidth: 0, flex: 1 }}><strong>{d.title}</strong><div className="muted tiny">{d.category} · {d.characters.toLocaleString()} characters</div><p className="muted tiny">{d.preview}{d.characters > 220 ? '…' : ''}</p>
                <button className="btn btn-ghost" disabled={busy === `summary-${d.id}`} onClick={() => summarize(d.id)}>{busy === `summary-${d.id}` ? 'Summarizing…' : 'Summarize with AI'}</button>
                <button className="btn btn-ghost danger" disabled={busy === `delete-${d.id}`} onClick={() => remove(d)}>Delete</button>
              </div>
            </div>)}
          </div>}
        </div>
      </section>

      <section className="panel" style={{ padding: 22 }}>
        <div className="eyebrow">02 · Ask your documents</div><h2>Grounded HR Q&A</h2>
        <p className="muted">Answers use retrieved passages from your uploaded policies and show their sources.</p>
        <form className="form" onSubmit={ask}>
          <label>Your question<textarea rows="4" value={question} onChange={e => setQuestion(e.target.value)} maxLength={500} minLength={2} placeholder="e.g. How many annual leave days are provided by this policy?" required /></label>
          <button className="btn btn-primary" disabled={busy === 'ask' || !docs.length}>{busy === 'ask' ? 'Searching & analyzing…' : 'Ask documents'}</button>
        </form>
        {answer && <div className="result-card" style={{ marginTop: 20 }}><div className="row-inline"><strong>Answer</strong><span className={`badge ${answer.ai_powered ? 'badge-ok' : 'badge-warn'}`}>{answer.ai_powered ? 'Gemini AI' : 'Retrieved text / AI unavailable'}</span></div><p style={{ whiteSpace: 'pre-wrap' }}>{answer.answer}</p>{answer.sources?.length > 0 && <><h4>Sources</h4>{answer.sources.map(s => <div key={s.id} className="source-box"><strong>{s.title}</strong>{s.passages.map((p, i) => <p key={i} className="muted tiny">“{p}”</p>)}</div>)}</>}</div>}
      </section>
    </div>

    <section className="panel" style={{ padding: 22, marginTop: 18 }}>
      <div className="eyebrow">03 · Version review</div><h2>Compare two documents</h2><p className="muted">Select two uploaded versions to identify additions, removals and changes that need human review.</p>
      <form className="form" onSubmit={compare}>
        <div className="form-row"><label>Document A<select value={compareA} onChange={e => setCompareA(e.target.value)} required><option value="">Select first document</option>{docs.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}</select></label>
          <label>Document B<select value={compareB} onChange={e => setCompareB(e.target.value)} required><option value="">Select second document</option>{docs.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}</select></label></div>
        <div><button className="btn btn-primary" disabled={busy === 'compare' || docs.length < 2}>{busy === 'compare' ? 'Comparing…' : 'Compare with AI'}</button></div>
      </form>
      {comparison && <div className="result-card" style={{ marginTop: 18 }}><h3>{comparison.document_a} vs. {comparison.document_b}</h3><p style={{ whiteSpace: 'pre-wrap' }}>{comparison.comparison}</p><p className="muted tiny">AI-assisted comparison; verify important policy or legal changes with HR/legal counsel.</p></div>}
    </section>

    {summary && <div className="overlay" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) setSummary(null) }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="summary-title"><div className="modal-head"><div><div className="eyebrow">AI summary</div><h2 id="summary-title">{summary.title}</h2></div><button className="btn" onClick={() => setSummary(null)}>Close</button></div><span className={`badge ${summary.ai_powered ? 'badge-ok' : 'badge-warn'}`}>{summary.ai_powered ? 'Generated with AI' : 'AI unavailable · fallback outline'}</span><div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, marginTop: 16 }}>{summary.summary}</div></section></div>}
  </>
}
