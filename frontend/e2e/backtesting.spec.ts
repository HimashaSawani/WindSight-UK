import { expect, test } from '@playwright/test'

test('backtesting route exposes API errors and rejects duplicate cutoffs', async ({ page }) => {
  await page.route('**/api/**', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Synthetic API failure for test' } }),
  )
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/backtesting')

  await expect(page.getByRole('heading', { name: 'Backtesting lab' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible()
  await expect(page.getByText('Synthetic API failure for test')).toBeVisible()

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    page: document.documentElement.scrollWidth,
  }))
  expect(dimensions.page).toBeLessThanOrEqual(dimensions.viewport)

  await page.getByLabel('Second cutoff').fill('09:00')
  await page.getByRole('button', { name: 'Run backtest' }).click()
  await expect(page.getByText('Choose two different cutoff times.')).toBeVisible()
})
