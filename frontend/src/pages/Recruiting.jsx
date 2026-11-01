import { useState } from 'react'
import { api } from '../api.js'
import { Badge, Empty, Modal, Notice } from '../components/ui.jsx'
import { useApi } from '../hooks.js'
import { downloadBlob, fmtDate, scoreTone } from '../utils.js'

const STATUS_TONE = { new: 'plain', shortlisted: 'ok', rejected: 'bad' }
const cap = (s) => s[0].toUpperCase() + s.slice(1)

function ApplicationDetail({ app, onClose, onChanged }) {
  const a = app.analysis
  const setStatus = async (status) => {
    await api.patch(`/applications/${app.id}`, { status })
    onChanged()
  }
  const download = async () => downloadBlob(await api.blob(`/applications/${app.id}/cv`), app.cv_filename)
  const remove = async () => {
    if (!window.confirm('Delete this application and its CV file?')) return
    await api.del(`/applications/${app.id}`)
    onChanged()
  }

  return (
    <Modal title={app.candidate_name} onClose={onClose}>
      <p className="muted small">{app.candidate_email} · applied for {app.job.title} on {fmtDate(app.created_at.slice(0, 10))}</p>

      <div className="score-box">
        <Badge tone={scoreTone(app.score)}>{app.score} / 100</Badge>
        <strong>{a.label}</strong>
      </div>

      <h3>CV summary</h3>
      <p>{a.summary}</p>

      <h3>Required skills</h3>
      <ul className="tags">
        {a.matched_skills.map((s) => <li key={s} className="tag-ok">{s}</li>)}
        {a.missing_skills.map((s) => <li key={s} className="tag-bad">{s} (missing)</li>)}
        {a.matched_skills.length + a.missing_skills.length === 0 && <li>No skills required for this role</li>}
      </ul>

      <h3>How the score adds up</h3>
      <p className="muted small">
        Skills {a.breakdown.skills}/60 · Experience {a.breakdown.experience}/30 · Education {a.breakdown.education}/10
      </p>

      {app.cover_note && (
        <>
          <h3>Note from candidate</h3>
          <p>{app.cover_note}</p>
        </>
      )}

      <footer className="form-actions spread">
        <div className="actions">
          <button className="btn" onClick={download}>Download CV</button>
          <button className="btn btn-ghost danger" onClick={remove}>Delete</button>
        </div>
        <div className="actions">
          {app.status !== 'rejected' && <button className="btn" onClick={() => setStatus('rejected')}>Reject</button>}
          {app.status !== 'shortlisted' && <button className="btn btn-ok" onClick={() => setStatus('shortlisted')}>Shortlist</button>}
        </div>
      </footer>
    </Modal>
  )
}


function HRUploadForm({ jobs, onClose, onSaved }) {
  const [form, setForm] = useState({ job_id: '', candidate_name: '', candidate_email: '', cover_note: '' })
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (key) => (e) => setForm((old) => ({ ...old, [key]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    if (!file) return setError('Choose a CV file first.')
    if (!form.job_id) return setError('Choose the job this candidate is applying for.')
    setBusy(true)
    setError('')
    const body = new FormData()
    Object.entries(form).forEach(([key, value]) => body.append(key, value))
    body.append('cv', file)
    try {
      await api.post('/applications/upload', body)
      onSaved()
    } catch (err) {
      setError(err.message || 'The CV could not be uploaded.')
      setBusy(false)
    }
  }

  return (
    <Modal title="Add candidate CV" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <p className="muted small">Upload a CV received by email or another channel. It will be analysed against the selected role and added to Applications.</p>
        <label>Job role
          <select required value={form.job_id} onChange={set('job_id')}>
            <option value="">Select a role</option>
            {jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
          </select>
        </label>
        <label>Candidate full name<input required maxLength={120} value={form.candidate_name} onChange={set('candidate_name')} /></label>
        <label>Candidate email<input required type="email" value={form.candidate_email} onChange={set('candidate_email')} /></label>
        <label>CV (PDF, DOCX or TXT, max 5 MB)
          <input required type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <label>HR note (optional)<textarea rows={3} maxLength={1000} value={form.cover_note} onChange={set('cover_note')} /></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <footer className="form-actions">
          <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button className="btn btn-primary" disabled={busy || jobs.length === 0}>{busy ? 'Uploading and scoring…' : 'Upload CV & score'}</button>
        </footer>
      </form>
    </Modal>
  )
}

function JobForm({ job, onClose, onSaved }) {
  const [form, setForm] = useState(
    job
      ? { ...job, required_skills: job.required_skills.join(', ') }
      : { title: '', department: '', description: '', required_skills: '', min_years: 0, status: 'open' },
  )
  const [error, setError] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    const body = {
      title: form.title,
      department: form.department,
      description: form.description,
      required_skills: form.required_skills.split(',').map((s) => s.trim()).filter(Boolean),
      min_years: Number(form.min_years),
      status: form.status,
    }
    try {
      if (job) await api.put(`/jobs/${job.id}`, body)
      else await api.post('/jobs', body)
      onSaved()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Modal title={job ? 'Edit role' : 'New role'} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>Title<input required value={form.title} onChange={set('title')} /></label>
        <div className="form-row">
          <label>Department<input value={form.department} onChange={set('department')} /></label>
          <label>Minimum years<input type="number" min="0" max="40" value={form.min_years} onChange={set('min_years')} /></label>
        </div>
        <label>Description<textarea rows={3} value={form.description} onChange={set('description')} /></label>
        <label>
          Required skills, separated by commas
          <input placeholder="python, sql, docker" value={form.required_skills} onChange={set('required_skills')} />
        </label>
        <label>
          Status
          <select value={form.status} onChange={set('status')}>
            <option value="open">Open for applications</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        {error && <p className="form-error">{error}</p>}
        <footer className="form-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary">Save role</button>
        </footer>
      </form>
    </Modal>
  )
}

export default function Recruiting() {
  const [tab, setTab] = useState('applications')
  const [jobFilter, setJobFilter] = useState('')
  const [viewing, setViewing] = useState(null)
  const [editingJob, setEditingJob] = useState(null) // null | 'new' | job
  const [uploadingCV, setUploadingCV] = useState(false)

  const apps = useApi(`/applications${jobFilter ? `?job_id=${jobFilter}` : ''}`)
  const jobs = useApi('/jobs/manage')
  const reloadAll = () => {
    apps.reload()
    jobs.reload()
  }

  const removeJob = async (j) => {
    if (!window.confirm(`Delete "${j.title}" and its ${j.application_count} applications?`)) return
    await api.del(`/jobs/${j.id}`)
    reloadAll()
  }

  return (
    <>
      <header className="page-head">
        <div>
          <div className="eyebrow">Hiring pipeline</div>
          <h1>Recruiting</h1>
          <p className="muted">Applications are ranked by how well each CV fits the role.</p>
        </div>
        <div className="actions">
          {tab === 'applications' && <button className="btn btn-primary" onClick={() => setUploadingCV(true)}>Upload candidate CV</button>}
          {tab === 'roles' && <button className="btn btn-primary" onClick={() => setEditingJob('new')}>New role</button>}
        </div>
      </header>

      <div className="tabs" role="tablist">
        {[['applications', 'Applications'], ['roles', 'Roles']].map(([id, label]) => (
          <button key={id} role="tab" aria-selected={tab === id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'applications' && (
        <>
          <div className="toolbar">
            <select aria-label="Filter by role" value={jobFilter} onChange={(e) => setJobFilter(e.target.value)}>
              <option value="">All roles</option>
              {(jobs.data ?? []).map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
            </select>
          </div>
          {apps.error && <Notice error={apps.error} onRetry={apps.reload} />}
          {jobs.data?.length === 0 && <Notice error="Create a job role first before uploading a candidate CV." />}
          {apps.data && apps.data.length === 0 && (
            <Empty title="No applications yet">Candidates can apply through Careers from the sign-in screen, or HR can upload a CV here using “Upload candidate CV”.</Empty>
          )}
          {apps.data && apps.data.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Candidate</th><th>Role</th><th>CV rating</th><th>Status</th><th /></tr>
                </thead>
                <tbody>
                  {apps.data.map((a) => (
                    <tr key={a.id}>
                      <td>
                        <div className="person-name">{a.candidate_name}</div>
                        <div className="muted small">{a.candidate_email}</div>
                      </td>
                      <td>{a.job.title}</td>
                      <td><Badge tone={scoreTone(a.score)}>{a.score} / 100</Badge></td>
                      <td><Badge tone={STATUS_TONE[a.status]}>{cap(a.status)}</Badge></td>
                      <td className="actions"><button className="btn" onClick={() => setViewing(a)}>Review</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === 'roles' && (
        <>
          {jobs.error && <Notice error={jobs.error} onRetry={jobs.reload} />}
          {jobs.data && jobs.data.length === 0 && <Empty title="No roles yet">Create a role so candidates can apply.</Empty>}
          {jobs.data && jobs.data.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Role</th><th>Required skills</th><th>Applications</th><th>Status</th><th /></tr>
                </thead>
                <tbody>
                  {jobs.data.map((j) => (
                    <tr key={j.id}>
                      <td>
                        <div className="person-name">{j.title}</div>
                        <div className="muted small">{[j.department, j.min_years ? `${j.min_years}+ years` : null].filter(Boolean).join(' · ')}</div>
                      </td>
                      <td>{j.required_skills.join(', ') || <span className="muted">None</span>}</td>
                      <td>{j.application_count}</td>
                      <td><Badge tone={j.status === 'open' ? 'ok' : 'plain'}>{cap(j.status)}</Badge></td>
                      <td className="actions">
                        <button className="btn btn-ghost" onClick={() => setEditingJob(j)}>Edit</button>
                        <button className="btn btn-ghost danger" onClick={() => removeJob(j)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {uploadingCV && (
        <HRUploadForm
          jobs={(jobs.data ?? []).filter((job) => job.status === 'open')}
          onClose={() => setUploadingCV(false)}
          onSaved={() => { setUploadingCV(false); reloadAll() }}
        />
      )}
      {viewing && (
        <ApplicationDetail
          app={viewing}
          onClose={() => setViewing(null)}
          onChanged={() => {
            setViewing(null)
            reloadAll()
          }}
        />
      )}
      {editingJob && (
        <JobForm
          job={editingJob === 'new' ? null : editingJob}
          onClose={() => setEditingJob(null)}
          onSaved={() => {
            setEditingJob(null)
            reloadAll()
          }}
        />
      )}
    </>
  )
}
