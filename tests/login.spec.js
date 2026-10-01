import { test, expect } from '@playwright/test'

test('staff user can sign in and open the dashboard', async ({ page }) => {
  const username = process.env.SADACO_TEST_USERNAME || 'safumk'
  const password = process.env.SADACO_TEST_PASSWORD
  test.skip(!password, 'Set SADACO_TEST_PASSWORD before running the authenticated E2E test.')

  const apiFailures = []
  page.on('response', (response) => {
    if (response.url().includes('/api/') && response.status() >= 500) {
      apiFailures.push(`${response.status()} ${response.url()}`)
    }
  })

  const consoleErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })

  await page.goto('/login')

  await expect(page.getByText('SADACO', { exact: true })).toBeVisible()
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: /sign in/i }).click()

  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByText('Dashboard', { exact: true }).first()).toBeVisible()

  expect(apiFailures, `API 5xx responses: ${apiFailures.join(', ')}`).toEqual([])
  expect(consoleErrors, `Browser console errors: ${consoleErrors.join(' | ')}`).toEqual([])
})
