import { useState } from 'react'
import { api } from '../api.js'
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
      // Do not trust the login response alone: confirm that the browser stored
      // and sends the HttpOnly session cookie before entering the application.
      await api.post('/auth/login', { email, password })
      const authenticatedUser = await api.get('/auth/me')
      onLogin(authenticatedUser)
    } catch (err) {
      const message = err?.message || 'Sign-in failed. Please try again.'
      const sessionCheckFailed = /sign in|session has expired|401/i.test(message)
      setError(sessionCheckFailed
        ? 'Your credentials were accepted, but the browser did not send the session cookie. For local testing, run the backend with HRINONE_ENV=development and HRINONE_COOKIE_SECURE=false, then refresh the page.'
        : message)
    } finally {
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
