import { fullName } from '../utils.js'

const HUES = [265, 18, 150, 200, 330, 45, 100]

export function Brand({ size = 'md', tagline = false }) {
  return (
    <div className={`brand brand-${size}`}>
      <img className="brand-logo" src="/logo.png" alt="HR1" width="720" height="448" />
      {tagline && <small>People, time off and hiring</small>}
    </div>
  )
}

export function Avatar({ person, size = 36 }) {
  const initials = (person.first_name[0] + person.last_name[0]).toUpperCase()
  const hue = HUES[(person.id ?? 0) % HUES.length]
  return (
    <span
      className="avatar"
      style={{ width: size, height: size, background: `hsl(${hue} 55% 92%)`, color: `hsl(${hue} 55% 28%)` }}
      aria-hidden="true"
    >
      {initials}
    </span>
  )
}

export function Person({ person, sub }) {
  return (
    <div className="person">
      <Avatar person={person} />
      <div>
        <div className="person-name">{fullName(person)}</div>
        <div className="muted small">{sub ?? person.job_title}</div>
      </div>
    </div>
  )
}

export function Badge({ tone, children }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

export function Modal({ title, onClose, children, wide = false }) {
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'modal-wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <header className="modal-head">
          <h2>{title}</h2>
          <button className="btn btn-ghost" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>
        {children}
      </div>
    </div>
  )
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      <p className="muted">{children}</p>
    </div>
  )
}

export function Notice({ error, onRetry }) {
  return (
    <div className="notice" role="alert">
      <div>
        <strong>Couldn't reach the server.</strong>
        <div className="small">{error.message}. Check that the API is running on port 8000.</div>
      </div>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
