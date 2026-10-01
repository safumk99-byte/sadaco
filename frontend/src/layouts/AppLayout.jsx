import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import NotificationBell from '../components/NotificationBell'

const managementLinks = [
  ['/staff', 'Staff Management'], ['/products', 'Products'], ['/products/stock', 'Stock Management'], ['/sales', 'Sales'], ['/production', 'Production'],
  ['/quality', 'Quality'], ['/inventory', 'Inventory'], ['/purchase', 'Purchase'], ['/finance', 'Finance'],
  ['/delivery', 'Delivery'], ['/marketing', 'Marketing'], ['/reports', 'Reports & Analytics'],
]
const staffLinks = [['/staff/tasks', 'My Tasks'], ['/staff/attendance', 'My Attendance'], ['/staff/performance', 'My Performance'], ['/sales/customer-requests', 'My Customer Requests'], ['/sales/enquiries', 'My Enquiries'], ['/production/jobs', 'My Production Jobs']]

export default function AppLayout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const management = user?.is_superuser || ['super_admin', 'institution_admin', 'manager'].includes(user?.role)
  const links = management ? managementLinks : staffLinks

  async function handleLogout() { await signOut(); navigate('/login', { replace: true }) }

  const Nav = () => <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto p-3">
    <NavLink to="/" end className={navClass}>⌂ <span>Dashboard</span></NavLink>
    {management && <NavLink to="/users" className={navClass}>◉ <span>Users & Roles</span></NavLink>}
    {links.map(([to, label]) => <NavLink key={to} to={to} className={navClass}>{label === 'Reports & Analytics' ? '▥' : '•'} <span>{label}</span></NavLink>)}
    {management && <NavLink to="/approvals" className={navClass}>✓ <span>Approval Center</span></NavLink>}
    {management && <NavLink to="/audit-log" className={navClass}>⌁ <span>Audit Trail</span></NavLink>}
    <NavLink to="/profile" className={navClass}>◎ <span>My Profile</span></NavLink>
  </nav>

  return <div className="min-h-screen bg-slate-100">
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-slate-200 bg-slate-950 text-white lg:flex">
      <SidebarHeader /><Nav /> <SidebarUser />
    </aside>
    {mobileOpen && <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={() => setMobileOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-slate-950 text-white transition-transform lg:hidden ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}><SidebarHeader /><Nav /><SidebarUser /></aside>
    <main className="lg:pl-64">
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">
        <div className="flex items-center gap-3"><button className="rounded-lg border border-slate-200 px-3 py-2 lg:hidden" onClick={() => setMobileOpen(true)}>☰</button><div><div className="font-semibold text-slate-900">SADACO Management System</div><div className="text-xs text-slate-500">React + Vite</div></div></div>
        <div className="flex items-center gap-2"><NotificationBell /><div className="hidden text-right sm:block"><div className="text-sm font-medium">{user?.name || user?.username}</div><div className="text-xs text-slate-500">{user?.role_label || user?.role}</div></div><button onClick={handleLogout} className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50">Sign out</button></div>
      </header>
      <section className="p-4 sm:p-6"><Outlet /></section>
    </main>
  </div>

  function SidebarHeader() { return <div className="border-b border-white/10 px-5 py-5"><div className="text-xl font-bold tracking-wide">SADACO</div><div className="text-xs text-slate-400">Management System</div></div> }
  function SidebarUser() { return <div className="mt-auto flex-shrink-0 border-t border-white/10 bg-slate-950 p-4"><div className="mb-3 text-sm font-medium">{user?.name || user?.username}<div className="text-xs text-slate-400">{user?.role_label}</div></div><button onClick={handleLogout} className="w-full rounded-lg border border-white/10 px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/5">↪ Sign out</button></div> }
  function navClass({ isActive }) { return `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${isActive ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white'}` }
}
