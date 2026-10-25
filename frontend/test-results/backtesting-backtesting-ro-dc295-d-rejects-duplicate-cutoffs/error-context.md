# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: backtesting.spec.ts >> backtesting route exposes API errors and rejects duplicate cutoffs
- Location: e2e\backtesting.spec.ts:3:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/HTTP 503/)
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText(/HTTP 503/) with timeout 5000ms
  - waiting for getByText(/HTTP 503/)

```

```yaml
- complementary:
  - paragraph: WindSight UK
  - paragraph: Forecast intelligence
  - navigation "Main navigation":
    - link "Overview":
      - /url: /overview
    - link "Forecast explorer":
      - /url: /forecasts
    - link "Accuracy analysis":
      - /url: /accuracy
    - link "Historical analysis":
      - /url: /history
    - link "Backtesting lab":
      - /url: /backtesting
    - link "Data & methodology":
      - /url: /methodology
  - text: Decision support only · Not a trading platform
- banner:
  - paragraph: UK wind generation
  - paragraph: "Decisions: 2026-01-01 through 2026-01-31"
  - text: Decision date period
  - combobox "Decision date period":
    - option "All January 2026" [selected]
    - option "1 Jan decision"
    - option "2 Jan decision"
    - option "3 Jan decision"
    - option "4 Jan decision"
    - option "5 Jan decision"
    - option "6 Jan decision"
    - option "7 Jan decision"
    - option "8 Jan decision"
    - option "9 Jan decision"
    - option "10 Jan decision"
    - option "11 Jan decision"
    - option "12 Jan decision"
    - option "13 Jan decision"
    - option "14 Jan decision"
    - option "15 Jan decision"
    - option "16 Jan decision"
    - option "17 Jan decision"
    - option "18 Jan decision"
    - option "19 Jan decision"
    - option "20 Jan decision"
    - option "21 Jan decision"
    - option "22 Jan decision"
    - option "23 Jan decision"
    - option "24 Jan decision"
    - option "25 Jan decision"
    - option "26 Jan decision"
    - option "27 Jan decision"
    - option "28 Jan decision"
    - option "29 Jan decision"
    - option "30 Jan decision"
    - option "31 Jan decision"
  - text: API unavailable
- main:
  - paragraph: Historical point-in-time evaluation
  - heading "Backtesting lab" [level=1]
  - paragraph: Reconstruct forecasts available by two decision cutoffs for 2026-01-01 through 2026-01-31. Later publications are excluded from each historical decision.
  - heading "Choose decision cutoffs" [level=2]
  - paragraph: Times are interpreted in Europe/London, including daylight-saving rules.
  - text: First cutoff
  - textbox "First cutoff": 09:00
  - text: Second cutoff
  - textbox "Second cutoff": 12:00
  - button "Run backtest"
  - alert:
    - paragraph: Could not load live data
    - paragraph: Synthetic API failure for test
    - button "Retry"
  - text: "Data source: Elexon BMRS · Timestamps stored in UTC and shown in Europe/London. No forecast is selected unless its publication time is at or before the decision cutoff."
```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test'
  2  | 
  3  | test('backtesting route exposes API errors and rejects duplicate cutoffs', async ({ page }) => {
  4  |   await page.route('**/api/**', (route) =>
  5  |     route.fulfill({ status: 503, json: { detail: 'Synthetic API failure for test' } }),
  6  |   )
  7  |   await page.goto('/backtesting')
  8  | 
  9  |   await expect(page.getByRole('heading', { name: 'Backtesting lab' })).toBeVisible()
> 10 |   await expect(page.getByText(/HTTP 503/)).toBeVisible()
     |                                            ^ Error: expect(locator).toBeVisible() failed
  11 | 
  12 |   await page.getByLabel('Second cutoff').fill('09:00')
  13 |   await page.getByRole('button', { name: 'Run backtest' }).click()
  14 |   await expect(page.getByRole('alert')).toHaveText('Choose two different cutoff times.')
  15 | })
  16 | 
```