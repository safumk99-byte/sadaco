import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './layouts/AppLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import UsersManagement from './pages/UsersManagement'
import MyProfile from './pages/MyProfile'
import StaffAttendance from './pages/StaffAttendance'
import StaffPerformance from './pages/StaffPerformance'
import ApprovalCenter from './pages/ApprovalCenter'
import AuditTrail from './pages/AuditTrail'
import CustomerRequests from './pages/CustomerRequests'
import StaffManagement from './pages/StaffManagement'
import StaffDetail from './pages/StaffDetail'
import StaffTasks from './pages/StaffTasks'
import ProductManagement from './pages/ProductManagement'
import ProductDetail from './pages/ProductDetail'
import StockManagement from './pages/StockManagement'
import SalesManagement from './pages/SalesManagement'
import ProductionManagement from './pages/ProductionManagement'
import QualityManagement from './pages/QualityManagement'
import PurchaseManagement from './pages/PurchaseManagement'
import FinanceManagement from './pages/FinanceManagement'
import DeliveryManagement from './pages/DeliveryManagement'
import MarketingManagement from './pages/MarketingManagement'
import ReportsManagement from './pages/ReportsManagement'
import CustomerPortal from './pages/CustomerPortal'
import CustomerRegister from './pages/CustomerRegister'
import './index.css'

const modules = [
  ['staff', 'Staff Management'], ['products', 'Products'], ['sales', 'Sales'], ['production', 'Production'],
  ['quality', 'Quality'], ['inventory', 'Inventory'], ['purchase', 'Purchase'], ['finance', 'Finance'],
  ['delivery', 'Delivery'], ['marketing', 'Marketing'], ['reports', 'Reports & Analytics'], ['users', 'Users & Roles'],
  ['approvals', 'Approval Center'], ['audit-log', 'Audit Trail'], ['profile', 'My Profile'],
  ['staff/tasks', 'My Tasks'], ['staff/attendance', 'My Attendance'], ['staff/performance', 'My Performance'],
  ['sales/customer-requests', 'My Customer Requests'], ['sales/enquiries', 'My Enquiries'], ['production/jobs', 'My Production Jobs'],
]

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<CustomerRegister />} />
          <Route element={<ProtectedRoute />}>
            <Route path="customer" element={<CustomerPortal />} />
            <Route element={<AppLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="staff" element={<StaffManagement />} />
              <Route path="staff/tasks" element={<StaffTasks />} />
              <Route path="staff/:id" element={<StaffDetail />} />
              <Route path="products" element={<ProductManagement />} />
              <Route path="products/stock" element={<StockManagement />} />
              <Route path="inventory" element={<StockManagement />} />
              <Route path="products/:id" element={<ProductDetail />} />
              <Route path="sales" element={<SalesManagement />} />
              <Route path="production" element={<ProductionManagement />} />
              <Route path="quality" element={<QualityManagement />} />
              <Route path="purchase" element={<PurchaseManagement />} />
              <Route path="finance" element={<FinanceManagement />} />
              <Route path="delivery" element={<DeliveryManagement />} />
              <Route path="marketing" element={<MarketingManagement />} />
              <Route path="reports" element={<ReportsManagement />} />
              <Route path="users" element={<UsersManagement />} />
              <Route path="approvals" element={<ApprovalCenter />} />
              <Route path="audit-log" element={<AuditTrail />} />
              <Route path="profile" element={<MyProfile />} />
              <Route path="staff/attendance" element={<StaffAttendance />} />
              <Route path="staff/performance" element={<StaffPerformance />} />
              <Route path="sales/customer-requests" element={<CustomerRequests />} />
              <Route path="sales/enquiries" element={<SalesManagement />} />
              <Route path="production/jobs" element={<ProductionManagement />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
