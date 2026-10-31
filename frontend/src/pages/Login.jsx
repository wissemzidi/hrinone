import { useState } from 'react'
import { api, auth } from '../api.js'
import { Brand } from '../components/ui.jsx'

export default function Login({ onLogin, onCareers }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const { token, user } = await api.post('/auth/login', { email, password })
      auth.set(token)
      onLogin(user)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <section className="login-side">
        <Brand size="lg" />
        <div>
          <h1>People, time off and hiring in one place.</h1>
          <p>Every approval and every hiring decision stays with you.</p>
        </div>
      </section>
      <section className="login-main">
        <form className="form login-form" onSubmit={submit}>
          <h2>Sign in to HR1</h2>
          <label>
            Work email
            <input type="email" required autoFocus autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="btn btn-primary" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
          <p className="muted small login-careers">
            Looking for a job?{' '}
            <button type="button" className="link" onClick={onCareers}>
              See open roles
            </button>
          </p>
        </form>
      </section>
    </div>
  )
}
