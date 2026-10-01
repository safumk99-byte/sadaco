import { test, expect } from '@playwright/test'

const routes = [
  { path: '/', name: 'Dashboard', heading: 'Dashboard' },
  { path: '/staff', name: 'Staff Management', heading: 'Staff Management' },
  { path: '/staff/tasks', name: 'My Tasks', heading: 'Staff Tasks' },
  { path: '/staff/attendance', name: 'My Attendance', heading: 'My Attendance' },
  { path: '/staff/performance', name: 'My Performance', heading: 'My Performance' },
  { path: '/products', name: 'Products', heading: 'Products & Inventory' },
  { path: '/products/stock', name: 'Stock Management', heading: 'Stock Management' },
  { path: '/sales', name: 'Sales', heading: 'Sales & CRM' },
  { path: '/sales/customer-requests', name: 'My Customer Requests', heading: 'Customer Requests' },
  { path: '/sales/enquiries', name: 'My Enquiries', heading: 'Sales & CRM' },
  { path: '/production', name: 'Production', heading: 'Production Management' },
  { path: '/production/jobs', name: 'My Production Jobs', heading: 'Production Management' },
  { path: '/quality', name: 'Quality', heading: 'Quality Management' },
  { path: '/purchase', name: 'Purchase', heading: 'Purchase Management' },
  { path: '/finance', name: 'Finance', heading: 'Finance & Accounts' },
  { path: '/delivery', name: 'Delivery', heading: /Delivery/ },
  { path: '/marketing', name: 'Marketing', heading: 'Marketing & Business Development' },
  { path: '/reports', name: 'Reports & Analytics', heading: 'Reports & Analytics' },
  { path: '/users', name: 'Users & Roles', heading: 'Users & Roles' },
  { path: '/approvals', name: 'Approval Center', heading: 'Approval Center' },
  { path: '/audit-log', name: 'Audit Trail', heading: 'Audit Trail' },
  { path: '/profile', name: 'My Profile', heading: 'My Profile' },
  { path: '/customer', name: 'Customer Portal', heading: 'Customer Portal' },
]

async function login(page) {
  const password = process.env.SADACO_TEST_PASSWORD
  test.skip(!password, 'Set SADACO_TEST_PASSWORD before running authenticated SADACO E2E tests.')

  await page.goto('/login')
  await expect(page.getByText('SADACO', { exact: true })).toBeVisible()
  await page.getByLabel('Username').fill(process.env.SADACO_TEST_USERNAME || 'safumk')
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible()
}

function attachDiagnostics(page) {
  const diagnostics = { api5xx: [], console: [], pageErrors: [], failedRequests: [] }

  page.on('response', (response) => {
    if (response.url().includes('/api/') && response.status() >= 500) {
      diagnostics.api5xx.push(`${response.status()} ${response.url()}`)
    }
  })
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.console.push(message.text())
  })
  page.on('pageerror', (error) => diagnostics.pageErrors.push(error.message))
  page.on('requestfailed', (request) => {
    const url = request.url()
    if (url.includes('/api/') || url.includes('/src/')) {
      diagnostics.failedRequests.push(`${request.method()} ${url} :: ${request.failure()?.errorText || 'failed'}`)
    }
  })

  return diagnostics
}

function assertDiagnostics(diagnostics, label) {
  expect(diagnostics.api5xx, `${label}: API 5xx responses`).toEqual([])
  expect(diagnostics.pageErrors, `${label}: uncaught page errors`).toEqual([])
  expect(diagnostics.console, `${label}: browser console errors`).toEqual([])
  expect(diagnostics.failedRequests, `${label}: failed API/source requests`).toEqual([])
}

test.describe('SADACO public pages', () => {
  test('login and customer registration pages load', async ({ page }) => {
    const diagnostics = attachDiagnostics(page)

    await page.goto('/login')
    await expect(page.getByText('SADACO', { exact: true })).toBeVisible()
    await expect(page.getByLabel('Username')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()

    await page.goto('/register')
    await expect(page.getByRole('heading', { name: 'Create Customer Account' })).toBeVisible()

    assertDiagnostics(diagnostics, 'public pages')
  })
})

test.describe('SADACO authenticated application', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('dashboard loads with navigation and user controls', async ({ page }) => {
    const diagnostics = attachDiagnostics(page)

    await expect(page.getByText('SADACO Management System')).toBeVisible()
    await expect(page.getByText('React + Vite')).toBeVisible()
    await expect(page.getByRole('button', { name: /sign out/i }).first()).toBeVisible()
    await expect(page.getByText('Users & Roles')).toBeVisible()
    await expect(page.getByText('Approval Center')).toBeVisible()
    await expect(page.getByText('Audit Trail')).toBeVisible()
    await expect(page.getByText('My Profile')).toBeVisible()

    assertDiagnostics(diagnostics, 'dashboard')
  })

  test('all authenticated React routes open and render their expected page', async ({ page }) => {
    const failures = []

    for (const route of routes) {
      const diagnostics = attachDiagnostics(page)
      await page.goto(route.path, { waitUntil: 'domcontentloaded' })

      try {
        await expect(page).toHaveURL(new RegExp(`${route.path.replaceAll('/', '\\/')}$`))
        await expect(page.getByRole('heading', { name: route.heading, exact: typeof route.heading === 'string' })).toBeVisible({ timeout: 10000 })
        assertDiagnostics(diagnostics, route.name)
      } catch (error) {
        failures.push(`${route.name} (${route.path}): ${error.message}`)
      }
    }

    expect(failures, `Route failures:\n${failures.join('\n')}`).toEqual([])
  })

  test('desktop sidebar navigation reaches every management module', async ({ page }) => {
    const diagnostics = attachDiagnostics(page)
    const links = [
      'Staff Management', 'Products', 'Stock Management', 'Sales', 'Production',
      'Quality', 'Inventory', 'Purchase', 'Finance', 'Delivery', 'Marketing',
      'Reports & Analytics', 'Users & Roles', 'Approval Center', 'Audit Trail', 'My Profile',
    ]

    for (const label of links) {
      const link = page.getByRole('link', { name: label, exact: true }).first()
      await expect(link, `Missing navigation link: ${label}`).toBeVisible()
    }

    assertDiagnostics(diagnostics, 'sidebar navigation')
  })

  test('mobile navigation opens and exposes the main menu', async ({ page }) => {
    const diagnostics = attachDiagnostics(page)
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')

    const menuButton = page.getByRole('button', { name: '☰' })
    await expect(menuButton).toBeVisible()
    await menuButton.click()
    await expect(page.getByText('SADACO', { exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'My Profile', exact: true })).toBeVisible()

    assertDiagnostics(diagnostics, 'mobile navigation')
  })

  test('authenticated user can sign out and is returned to login', async ({ page }) => {
    const diagnostics = attachDiagnostics(page)
    await page.getByRole('button', { name: /sign out/i }).first().click()
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByLabel('Username')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()

    assertDiagnostics(diagnostics, 'logout')
  })
})
