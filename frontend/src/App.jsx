import { useEffect, useState } from 'react'
import { api, setUnauthorizedHandler } from './api.js'
import Icon from './components/icons.jsx'
import NotificationBell from './components/NotificationBell.jsx'
import { Brand } from './components/ui.jsx'
import Careers from './pages/Careers.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Employees from './pages/Employees.jsx'
import Assistant from './pages/Assistant.jsx'
import Leaves from './pages/Leaves.jsx'
import Login from './pages/Login.jsx'
import MyLeaves from './pages/MyLeaves.jsx'
import MyTraining from './pages/MyTraining.jsx'
import Performance from './pages/Performance.jsx'
import Recruiting from './pages/Recruiting.jsx'
import Requests from './pages/Requests.jsx'
import Training from './pages/Training.jsx'
import DocumentIntelligence from './pages/DocumentIntelligence.jsx'
import Security from './pages/Security.jsx'
import { fullName } from './utils.js'

const ADMIN_PAGES = [
  { id: 'dashboard', label: 'Today', icon: 'today', Component: Dashboard },
  { id: 'performance', label: 'Performance', icon: 'performance', Component: Performance },
  { id: 'employees', label: 'People', icon: 'people', Component: Employees },
  { id: 'leaves', label: 'Time off', icon: 'calendar', Component: Leaves },
  { id: 'training', label: 'Training', icon: 'training', Component: Training },
  { id: 'recruiting', label: 'Recruiting', icon: 'briefcase', Component: Recruiting },
  { id: 'requests', label: 'Requests', icon: 'inbox', Component: Requests },
  { id: 'documents-ai', label: 'AI Documents', icon: 'document', Component: DocumentIntelligence },
  { id: 'security', label: 'Security', icon: 'shield', Component: Security },
]
const EMPLOYEE_PAGES = [
  { id: 'mine', label: 'My time off', icon: 'calendar', Component: MyLeaves },
  { id: 'training', label: 'My training', icon: 'training', Component: MyTraining },
  { id: 'assistant', label: 'HR assistant', icon: 'chat', Component: Assistant },
]

export default function App() {
  const [user, setUser] = useState(null)
  const [booting, setBooting] = useState(true)
  const [signedOutView, setSignedOutView] = useState('login') // 'login' | 'careers'
  const [page, setPage] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null))
    api.get('/auth/me')
      .then(setUser)
      .catch(() => {})
      .finally(() => setBooting(false))
  }, [])

  const signOut = async () => {
    try { await api.post('/auth/logout') } catch { /* local UI still signs out */ }
    setUser(null)
    setPage(null)
    setMenuOpen(false)
    setSignedOutView('login')
  }

  const goTo = (id) => {
    setPage(id)
    setMenuOpen(false)
  }

  if (booting) return <p className="muted boot">Loading…</p>

  if (!user) {
    return signedOutView === 'careers' ? (
      <Careers onBack={() => setSignedOutView('login')} />
    ) : (
      <Login
        onLogin={(u) => {
          setUser(u)
          setPage(null)
        }}
        onCareers={() => setSignedOutView('careers')}
      />
    )
  }

  const isAdmin = user.role === 'admin'
  const pages = isAdmin ? ADMIN_PAGES : EMPLOYEE_PAGES
  const current = pages.find((p) => p.id === page) ?? pages[0]
  const { Component } = current
  const displayName = user.employee ? fullName(user.employee) : 'Administrator'
  const initials = user.employee
    ? (user.employee.first_name[0] + user.employee.last_name[0]).toUpperCase()
    : 'AD'

  return (
    <div className="shell">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <Brand tagline />
        <nav aria-label="Main">
          {pages.map((p) => (
            <button
              key={p.id}
              className={`nav-item ${p.id === current.id ? 'active' : ''}`}
              aria-current={p.id === current.id ? 'page' : undefined}
              onClick={() => goTo(p.id)}
            >
              <span className="nav-icon">
                <Icon name={p.icon} />
              </span>
              {p.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-user">
          <div className="sidebar-id">
            <div className="top-avatar" aria-hidden="true">
              {initials}
            </div>
            <div>
              <div className="sidebar-name">{displayName}</div>
              <div className="sidebar-role">{isAdmin ? 'Admin' : user.employee?.job_title}</div>
            </div>
          </div>
          <button className="btn signout" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>
      {menuOpen && <div className="scrim" onClick={() => setMenuOpen(false)} />}

      <div className="main-area">
        <header className="topbar">
          <button className="mobile-menu" aria-label="Open menu" onClick={() => setMenuOpen(true)}>
            ☰
          </button>
          <div className="breadcrumbs">
            <strong>{current.label}</strong>
          </div>
          <div className="top-right">
            <NotificationBell />
            <div className="top-avatar" aria-hidden="true">
              {initials}
            </div>
          </div>
        </header>
        <main className="content">
          <Component user={user} goTo={goTo} />
        </main>
      </div>
    </div>
  )
}
