import { useState } from 'react'
import { api } from '../api.js'
import { Brand, Empty, Modal, Notice } from '../components/ui.jsx'
import { useApi } from '../hooks.js'

function ApplyForm({ job, onClose }) {
  const [form, setForm] = useState({ candidate_name: '', candidate_email: '', cover_note: '' })
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    if (!file) return setError('Attach your CV before sending')
    setBusy(true)
    setError(null)
    const body = new FormData()
    body.append('job_id', job.id)
    Object.entries(form).forEach(([k, v]) => body.append(k, v))
    body.append('cv', file)
    try {
      await api.post('/applications', body)
      setDone(true)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  if (done) {
    return (
      <Modal title="Application sent" onClose={onClose}>
        <p>Thanks, {form.candidate_name.split(' ')[0]}. We received your CV for {job.title} and will email you at {form.candidate_email}.</p>
        <footer className="form-actions">
          <button className="btn btn-primary" onClick={onClose}>Close</button>
        </footer>
      </Modal>
    )
  }

  return (
    <Modal title={`Apply for ${job.title}`} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Full name
          <input required value={form.candidate_name} onChange={set('candidate_name')} />
        </label>
        <label>
          Email
          <input required type="email" value={form.candidate_email} onChange={set('candidate_email')} />
        </label>
        <label>
          CV (PDF, DOCX or TXT, up to 5 MB)
          <input required type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files[0] ?? null)} />
        </label>
        <label>
          Note (optional)
          <textarea rows={3} maxLength={1000} value={form.cover_note} onChange={set('cover_note')} />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <footer className="form-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Sending…' : 'Send application'}</button>
        </footer>
      </form>
    </Modal>
  )
}

export default function Careers({ onBack }) {
  const { data: jobs, error, loading, reload } = useApi('/jobs')
  const [applying, setApplying] = useState(null)

  return (
    <div className="careers">
      <Brand />
      <header className="page-head">
        <div>
          <div className="eyebrow">Careers</div>
          <h1>Open roles</h1>
          <p className="muted">Pick a role and send your CV. It goes straight to our HR team.</p>
        </div>
        <button className="btn" onClick={onBack}>Back to sign in</button>
      </header>

      {error && <Notice error={error} onRetry={reload} />}
      {loading && <p className="muted">Loading…</p>}
      {jobs && jobs.length === 0 && <Empty title="No open roles right now">Check back soon.</Empty>}
      <div className="job-list">
        {(jobs ?? []).map((j) => (
          <article key={j.id} className="panel">
            <div className="panel-head">
              <h2>{j.title}</h2>
              <button className="btn btn-primary" onClick={() => setApplying(j)}>Apply</button>
            </div>
            <p className="muted small">{[j.department, j.min_years ? `${j.min_years}+ years` : null].filter(Boolean).join(' · ')}</p>
            <p className="job-desc">{j.description}</p>
            <ul className="tags">
              {j.required_skills.map((s) => <li key={s}>{s}</li>)}
            </ul>
          </article>
        ))}
      </div>
      {applying && <ApplyForm job={applying} onClose={() => setApplying(null)} />}
    </div>
  )
}
