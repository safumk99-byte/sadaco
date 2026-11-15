import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const MANAGEMENT_ROLES = ['super_admin', 'institution_admin', 'manager']
const GLOBAL_ADMIN_ROLES = ['super_admin', 'institution_admin']

function requiresManagementAccess(pathname) {
  if (pathname === '/staff' || /^\\/staff\\/[^/]+$/.test(pathname)) return true
  if (
    pathname === '/products' || pathname.startsWith('/products/') ||
    pathname === '/sales' ||
    pathname === '/production' ||
    ['/quality', '/purchase', '/finance', '/delivery', '/marketing', '/reports', '/approvals', '/audit-log'].some(
      (path) => pathname === path || pathname.startsWith(path + '/')
    )
  ) return true

  // These staff workspaces remain available to ordinary staff accounts.
  if (
    ['/staff/tasks', '/staff/attendance', '/staff/performance',
      '/sales/customer-requests', '/sales/enquiries', '/production/jobs'].some(
      (path) => pathname === path || pathname.startsWith(path + '/')
    )
  ) return false

  return false
}

export default function ProtectedRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div className="grid min-h-screen place-items-center text-slate-500">Loading SADACO…</div>
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  if (user.role === 'customer' && location.pathname !== '/customer') return <Navigate to="/customer" replace />
  if (user.role !== 'customer' && location.pathname === '/customer') return <Navigate to="/" replace />

  const role = user.is_superuser ? 'super_admin' : user.role
  const globalAdmin = GLOBAL_ADMIN_ROLES.includes(role)
  const management = MANAGEMENT_ROLES.includes(role)
  const globalAdminOnly = ['/users', '/departments'].some(
    (path) => location.pathname === path || location.pathname.startsWith(path + '/')
  )

  if (globalAdminOnly && !globalAdmin) return <Navigate to="/" replace />
  if (requiresManagementAccess(location.pathname) && !management) {
    return <Navigate to="/staff/tasks" replace />
  }

  return <Outlet />
}
