import { expect, test } from '@playwright/test'

test('backtesting route exposes API errors and rejects duplicate cutoffs', async ({ page }) => {
  await page.route('**/api/**', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Synthetic API failure for test' } }),
  )
  await page.goto('/backtesting')

  await expect(page.getByRole('heading', { name: 'Backtesting lab' })).toBeVisible()
  await expect(page.getByText(/HTTP 503/)).toBeVisible()

  await page.getByLabel('Second cutoff').fill('09:00')
  await page.getByRole('button', { name: 'Run backtest' }).click()
  await expect(page.getByRole('alert')).toHaveText('Choose two different cutoff times.')
})
