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

const icons = { Dashboard:'⌂', Users:'◉', Staff:'♙', Products:'□', Stock:'▤', Sales:'↗', Production:'⚙', Quality:'✓', Inventory:'▥', Purchase:'⇩', Finance:'◈', Delivery:'⇢', Marketing:'◇', Reports:'▥', Approvals:'✓', Audit:'⌁', Profile:'◎' }

export default function AppLayout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const management = user?.is_superuser || ['super_admin', 'institution_admin', 'manager'].includes(user?.role)
  const links = management ? managementLinks : staffLinks
  async function handleLogout() { await signOut(); navigate('/login', { replace: true }) }
  function handleNavClick() {
    setMobileOpen(false)
  }

  const navContent = <>
    <NavLink to="/" end className={navClass} onClick={handleNavClick}><span className="nav-icon">{icons.Dashboard}</span><span>Dashboard</span></NavLink>
    {management && <NavLink to="/users" className={navClass} onClick={handleNavClick}><span className="nav-icon">{icons.Users}</span><span>Users & Roles</span></NavLink>}
    {links.map(([to, label]) => <NavLink key={to} to={to} className={navClass} onClick={handleNavClick}><span className="nav-icon">{label === 'Reports & Analytics' ? icons.Reports : label.split(' ')[0] === 'Stock' ? icons.Stock : '•'}</span><span>{label}</span></NavLink>)}
    {management && <NavLink to="/approvals" className={navClass} onClick={handleNavClick}><span className="nav-icon">{icons.Approvals}</span><span>Approval Center</span></NavLink>}
    {management && <NavLink to="/audit-log" className={navClass} onClick={handleNavClick}><span className="nav-icon">{icons.Audit}</span><span>Audit Trail</span></NavLink>}
    <NavLink to="/profile" className={navClass} onClick={handleNavClick}><span className="nav-icon">{icons.Profile}</span><span>My Profile</span></NavLink>
  </>

  return <div className="min-h-screen bg-[#f5f7fb]">
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-slate-800/70 bg-[#111827] text-white lg:flex"><SidebarHeader /><nav className="sidebar-nav min-h-0 flex-1 space-y-1.5 overflow-y-auto overscroll-contain px-3 py-4">{navContent}</nav><SidebarUser /></aside>
    {mobileOpen && <div className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-[1px] lg:hidden" onClick={() => setMobileOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-[#111827] text-white shadow-2xl transition-transform lg:hidden ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}><SidebarHeader /><nav className="sidebar-nav min-h-0 flex-1 space-y-1.5 overflow-y-auto overscroll-contain px-3 py-4">{navContent}</nav><SidebarUser /></aside>
    <main className="lg:pl-64">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 shadow-sm shadow-slate-200/30 backdrop-blur-xl">
        <div className="flex h-[72px] items-center justify-between px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button aria-label="Open menu" className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600 lg:hidden" onClick={() => setMobileOpen(true)}>☰</button>
            <div className="flex min-w-0 items-center gap-3">
              <div className="hidden h-9 w-1 rounded-full bg-gradient-to-b from-blue-500 via-indigo-500 to-violet-600 sm:block" />
              <div className="min-w-0"><div className="truncate text-[15px] font-extrabold tracking-tight text-slate-900 sm:text-base">SADACO Management System</div><div className="hidden text-[11px] font-medium text-slate-400 sm:block">Operations & Business Management</div></div>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <NotificationBell />
            <div className="hidden items-center gap-2 border-l border-slate-200 pl-3 sm:flex"><div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-violet-600 text-xs font-bold text-white shadow-sm">{(user?.name || user?.username || 'U').charAt(0).toUpperCase()}</div><div className="max-w-[150px] text-right"><div className="truncate text-sm font-semibold text-slate-800">{user?.name || user?.username}</div><div className="truncate text-[11px] font-medium text-slate-400">{user?.role_label || user?.role}</div></div></div>
            <button onClick={handleLogout} aria-label="Sign out" title="Sign out" className="group flex h-10 items-center rounded-xl border border-slate-200 bg-white px-3.5 text-xs font-bold text-slate-600 shadow-sm transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600"><span className="hidden sm:inline">Sign out</span><span className="sm:hidden">Exit</span></button>
          </div>
        </div>
      </header>
      <section className="min-h-[calc(100vh-68px)] p-4 sm:p-6 lg:p-7"><Outlet /></section>
    </main>
  </div>

  function SidebarHeader() { return <div className="border-b border-white/10 px-5 py-5"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 via-indigo-500 to-violet-600 text-sm font-black shadow-lg shadow-indigo-950/30">S</div><div><div className="text-lg font-extrabold tracking-wide">SADACO</div><div className="text-[10px] font-medium uppercase tracking-[.18em] text-slate-400">Management System</div></div></div></div> }
  function SidebarUser() { return <div className="mt-auto flex-shrink-0 border-t border-white/10 bg-black/10 p-4"><div className="mb-3 flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-slate-600 to-slate-700 text-xs font-bold text-slate-100">{(user?.name || user?.username || 'U').charAt(0).toUpperCase()}</div><div className="min-w-0"><div className="truncate text-sm font-semibold">{user?.name || user?.username}</div><div className="truncate text-[11px] text-slate-400">{user?.role_label || user?.role}</div></div></div><button onClick={handleLogout} className="group flex w-full items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-xs font-bold text-slate-300 transition hover:border-rose-400/30 hover:bg-rose-500/10 hover:text-rose-200">Sign out</button></div> }
  function navClass({ isActive }) { return `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition ${isActive ? 'bg-blue-600 text-white shadow-lg shadow-blue-950/20' : 'text-slate-400 hover:bg-white/5 hover:text-white'}` }
}
