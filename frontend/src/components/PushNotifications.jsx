import { useState } from 'react'
import { getPushConfig, subscribePush } from '../services/api'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)))
}

export default function PushNotifications() {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  async function enable() {
    setBusy(true); setMessage('')
    try {
      if (!('Notification' in window) || !('serviceWorker' in navigator) || !('PushManager' in window)) throw new Error('This browser does not support web push notifications.')
      const config = await getPushConfig()
      if (!config.enabled || !config.public_key) throw new Error('Web Push is not configured on this server yet.')
      const permission = await Notification.requestPermission()
      if (permission !== 'granted') throw new Error('Notification permission was not granted.')
      const registration = await navigator.serviceWorker.register('/service-worker.js')
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(config.public_key) })
      await subscribePush(subscription.toJSON())
      setMessage('Phone notifications are enabled on this device.')
    } catch (error) { setMessage(error.message || 'Unable to enable notifications.') }
    finally { setBusy(false) }
  }

  return <button onClick={enable} disabled={busy} className="hidden xl:inline-flex rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60" title={message || 'Enable Web Push notifications'}>{busy ? 'Enabling…' : '🔔 Enable notifications'}</button>
}
