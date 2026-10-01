import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
})

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  return parts.length === 2 ? parts.pop().split(';').shift() : null
}

api.interceptors.request.use((config) => {
  const csrf = getCookie('csrftoken')
  if (csrf) config.headers['X-CSRFToken'] = csrf
  return config
})

export async function initCsrf() { await api.get('/auth/csrf/') }
export async function getCurrentUser() { return (await api.get('/auth/me/')).data }
export async function login(username, password) { return (await api.post('/auth/login/', { username, password })).data }
export async function logout() { return (await api.post('/auth/logout/')).data }
export async function getDashboard() { return (await api.get('/dashboard/')).data }
export async function getNotifications() { return (await api.get('/notifications/')).data }
export async function markNotificationRead(id) { return (await api.post(`/notifications/${id}/read/`)).data }
export async function markAllNotificationsRead() { return (await api.post('/notifications/read-all/')).data }
export async function getPushConfig() { return (await api.get('/push/config/')).data }
export async function subscribePush(subscription) { return (await api.post('/push/subscribe/', subscription)).data }
export async function unsubscribePush(endpoint = '') { return (await api.post('/push/unsubscribe/', { endpoint })).data }
export default api

export async function getPurchaseSummary() { return (await api.get('/purchase/summary/')).data }
export async function getPurchaseSuppliers(params = {}) { return (await api.get('/purchase/suppliers/', { params })).data }
export async function createPurchaseSupplier(data) { return (await api.post('/purchase/suppliers/create/', data)).data }
export async function updatePurchaseSupplier(id, data) { return (await api.post(`/purchase/suppliers/${id}/update/`, data)).data }
export async function getPurchaseOrders(params = {}) { return (await api.get('/purchase/orders/', { params })).data }
export async function createPurchaseOrder(data) { return (await api.post('/purchase/orders/create/', data)).data }
export async function getPurchaseOrder(id) { return (await api.get(`/purchase/orders/${id}/`)).data }
export async function receivePurchaseOrder(id, data) { return (await api.post(`/purchase/orders/${id}/receive/`, data)).data }

export async function getFinanceDashboard() { return (await api.get('/finance/dashboard/')).data }
export async function getExpenses(params = {}) { return (await api.get('/finance/expenses/', { params })).data }
export async function createExpense(data) { return (await api.post('/finance/expenses/create/', data)).data }
export async function createExpenseCategory(data) { return (await api.post('/finance/categories/create/', data)).data }
export async function getReceivables() { return (await api.get('/finance/receivables/')).data }
export async function getSupplierPayments() { return (await api.get('/finance/supplier-payments/')).data }
export async function createSupplierPayment(data) { return (await api.post('/finance/supplier-payments/create/', data)).data }
export async function getReconciliation(params = {}) { return (await api.get('/finance/reconciliation/', { params })).data }

export async function getDeliverySummary(params={}) { return (await api.get('/delivery/summary/', {params})).data }
export async function updateDelivery(id,data) { return (await api.post(`/delivery/orders/${id}/update/`,data)).data }
export async function saveDeliveryFeedback(id,data) { return (await api.post(`/delivery/orders/${id}/feedback/`,data)).data }
export async function getMarketingDashboard(params={}) { return (await api.get('/marketing/dashboard/',{params})).data }
export async function createCampaign(data) { return (await api.post('/marketing/campaigns/create/',data)).data }
export async function createMarketingContent(data) { return (await api.post('/marketing/content/create/',data)).data }
export async function createMarketingLead(data) { return (await api.post('/marketing/leads/create/',data)).data }
export async function getReportsDashboard(params={}) { return (await api.get('/reports/dashboard/',{params})).data }
