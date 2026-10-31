import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import Icon from './icons.jsx'
import { timeAgo } from '../utils.js'

const ICON = { training: 'training', document: 'document', question: 'chat', info: 'bell' }

export default function NotificationBell() {
  const [data, setData] = useState({ unread: 0, items: [] })
  const [open, setOpen] = useState(false)
  const box = useRef(null)

  const load = useCallback(() => {
    api.get('/notifications').then(setData).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 30000)
    return () => clearInterval(id)
  }, [load])

  useEffect(() => {
    if (!open) return
    const close = (e) => box.current && !box.current.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const toggle = () => {
    if (!open) load()
    setOpen(!open)
  }
  const readAll = async () => {
    await api.post('/notifications/read-all')
    load()
  }

  return (
    <div className="bell" ref={box}>
      <button className="bell-btn" onClick={toggle} aria-label={`Notifications, ${data.unread} unread`} aria-expanded={open}>
        <Icon name="bell" size={18} />
        {data.unread > 0 && <span className="bell-count">{data.unread > 9 ? '9+' : data.unread}</span>}
      </button>
      {open && (
        <div className="bell-panel" role="dialog" aria-label="Notifications">
          <div className="bell-head">
            <strong>Notifications</strong>
            {data.unread > 0 && (
              <button className="link small" onClick={readAll}>
                Mark all as read
              </button>
            )}
          </div>
          {data.items.length === 0 ? (
            <p className="muted small bell-empty">Nothing yet.</p>
          ) : (
            <ul className="bell-list">
              {data.items.map((n) => (
                <li key={n.id} className={n.is_read ? '' : 'unread'}>
                  <span className="bell-icon"><Icon name={ICON[n.kind] ?? ICON.info} size={16} /></span>
                  <div>
                    <div className="bell-title">{n.title}</div>
                    {n.body && <div className="muted small">{n.body}</div>}
                    <div className="faint tiny">{timeAgo(n.created_at)}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
