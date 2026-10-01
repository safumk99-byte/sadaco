import { useEffect, useRef, useState } from 'react'
import { getNotifications, markAllNotificationsRead, markNotificationRead } from '../services/api'

function timeAgo(value) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const ref = useRef(null)

  async function load() {
    try {
      const data = await getNotifications()
      setItems(data.notifications || [])
      setCount(data.count || 0)
    } catch {}
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 30000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    function close(event) { if (!ref.current?.contains(event.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  async function read(item) {
    if (!item.is_read) {
      await markNotificationRead(item.id)
      setItems((current) => current.map((n) => n.id === item.id ? { ...n, is_read: true } : n))
      setCount((value) => Math.max(0, value - 1))
    }
    if (item.url && item.url.startsWith('/')) window.location.href = item.url
  }

  async function readAll() {
    await markAllNotificationsRead()
    setItems((current) => current.map((n) => ({ ...n, is_read: true })))
    setCount(0)
  }

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-label="Notifications" className="relative rounded-xl border border-slate-200 bg-white p-2.5 text-lg shadow-sm hover:bg-slate-50">
        🔔
        {count > 0 && <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-600 px-1 text-center text-[10px] font-bold leading-5 text-white">{count > 99 ? '99+' : count}</span>}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-[min(380px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div><div className="font-semibold">Notifications</div><div className="text-xs text-slate-500">{count ? `${count} unread` : 'All caught up'}</div></div>
            {count > 0 && <button onClick={readAll} className="text-xs font-medium text-slate-600 hover:text-slate-950">Mark all read</button>}
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            {items.length ? items.map((item) => (
              <button key={item.id} onClick={() => read(item)} className={`flex w-full gap-3 border-b border-slate-100 px-4 py-3 text-left hover:bg-slate-50 ${!item.is_read ? 'bg-slate-50' : ''}`}>
                <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-900 text-xs font-bold text-white">{item.type?.[0]?.toUpperCase() || 'N'}</span>
                <span className="min-w-0"><span className="block text-sm font-semibold text-slate-900">{item.title}</span><span className="block truncate text-xs text-slate-600">{item.message}</span><span className="mt-1 block text-[11px] text-slate-400">{timeAgo(item.created_at)}</span></span>
              </button>
            )) : <div className="px-5 py-10 text-center text-sm text-slate-500">You're all caught up. ✓</div>}
          </div>
          <a href="/accounts/notifications/" className="block border-t border-slate-100 px-4 py-3 text-center text-sm font-medium text-slate-700 hover:bg-slate-50">View all notifications →</a>
        </div>
      )}
    </div>
  )
}
