import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const metrics = {
  observation_count: 2,
  matched_observations: 1,
  missing_forecasts: 1,
  missing_actuals: 0,
  forecast_coverage_pct: 50,
  actual_coverage_pct: 100,
  mean_forecast_mw: 100,
  mean_actual_mw: 95,
  mae_mw: 5,
  rmse_mw: 5,
  mean_bias_error_mw: 5,
  wape_pct: 5.26,
  maximum_absolute_error_mw: 5,
}

const daily = {
  decision_date: '2026-01-01',
  delivery_date: '2026-01-02',
  metrics,
}

const comparison = {
  decision_start: '2026-01-01',
  decision_end: '2026-01-01',
  decision_cutoff_local_time: '12:00:00',
  timezone: 'Europe/London',
  decision_dates: ['2026-01-01'],
  observation_count: 2,
  observations: [
    {
      decision_date: '2026-01-01',
      delivery_date: '2026-01-02',
      decision_cutoff: '2026-01-01T12:00:00Z',
      target_time: '2026-01-02T00:00:00Z',
      forecast_publish_time: '2026-01-01T11:00:00Z',
      forecast_mw: 100,
      actual_mw: 95,
      forecast_age_minutes: 60,
      availability: 'matched',
      error_mw: 5,
      conflicting_forecast_duplicate: false,
      conflicting_actual_duplicate: false,
      forecast_source_metadata: {},
      actual_source_metadata: {},
    },
    {
      decision_date: '2026-01-01',
      delivery_date: '2026-01-02',
      decision_cutoff: '2026-01-01T12:00:00Z',
      target_time: '2026-01-02T00:30:00Z',
      forecast_publish_time: null,
      forecast_mw: null,
      actual_mw: 90,
      forecast_age_minutes: null,
      availability: 'missing_forecast',
      error_mw: null,
      conflicting_forecast_duplicate: false,
      conflicting_actual_duplicate: false,
      forecast_source_metadata: null,
      actual_source_metadata: {},
    },
  ],
}

const dataQuality = {
  analytics_data_source: 'live_elexon',
  status: 'ok',
  last_operation: 'comparison',
  last_attempt: '2026-01-02T12:00:00Z',
  last_successful_refresh: '2026-01-02T12:00:00Z',
  raw_forecast_records: 2,
  normalized_forecast_records: 2,
  invalid_forecast_records: 0,
  raw_actual_records: 2,
  normalized_actual_records: 2,
  invalid_actual_records: 0,
  missing_forecast_records: 1,
  missing_actual_records: 0,
  forecast_source_latest_time: '2026-01-01T11:00:00Z',
  actual_source_latest_time: '2026-01-02T00:30:00Z',
  requests_made: 2,
  cache_hits: 1,
  failed_requests: 0,
  ingestion_enabled: false,
  stored_forecast_records: 0,
  stored_actual_records: 0,
  stored_rejected_records: 0,
  missing_actual_intervals: 0,
  duplicate_forecast_records: 0,
  duplicate_actual_records: 0,
  conflicting_forecast_groups: 0,
  conflicting_actual_groups: 0,
  off_grid_forecast_records: 0,
  message: 'Diagnostics response without newer optional archive fields.',
}

const performance = {
  uptime_seconds: 60,
  requests_in_window: 4,
  server_errors_in_window: 0,
  availability_pct: 100,
  mean_response_time_ms: 18,
  p95_response_time_ms: 25,
  total_requests: 4,
  total_server_errors: 0,
}

function accuracyResponse() {
  return {
    decision_cutoff_local_time: '12:00:00',
    timezone: 'Europe/London',
    decision_start: '2026-01-01',
    decision_end: '2026-01-01',
    by_decision_date: [daily],
    by_delivery_date: [daily],
    overall: metrics,
  }
}

function backtestCutoff(cutoff: string) {
  return {
    cutoff_local_time: cutoff,
    forecast_metrics: metrics,
    benchmark_forecast_metrics: metrics,
    persistence_metrics: metrics,
    persistence_matched_observations: 1,
  }
}

async function fulfillApi(route: import('@playwright/test').Route) {
  const path = new URL(route.request().url()).pathname
  const responses: Record<string, unknown> = {
    '/api/health': { status: 'healthy', service: 'windsight-uk-api' },
    '/api/overview': {
      decision_cutoff_local_time: '12:00:00',
      timezone: 'Europe/London',
      decision_start: '2026-01-01',
      decision_end: '2026-01-01',
      generated_at: '2026-01-02T12:00:00Z',
      metrics,
      daily_history: [daily],
    },
    '/api/comparison': comparison,
    '/api/accuracy': accuracyResponse(),
    '/api/history': {
      decision_cutoff_local_time: '12:00:00',
      timezone: 'Europe/London',
      decision_start: '2026-01-01',
      decision_end: '2026-01-01',
      days: [daily],
    },
    '/api/data-quality': dataQuality,
    '/api/performance': performance,
    '/api/forecast-revisions': {
      decision_date: '2026-01-01',
      delivery_date: '2026-01-02',
      target_time: '2026-01-02T00:00:00Z',
      decision_cutoff: '2026-01-01T12:00:00Z',
      decision_cutoff_local_time: '12:00:00',
      timezone: 'Europe/London',
      revisions: [
        {
          publish_time: '2026-01-01T11:00:00Z',
          generation_mw: 100,
          available_at_decision_time: true,
          selected_for_decision: true,
          duplicate_publication_timestamp: false,
          conflicting_duplicate: false,
        },
      ],
    },
    '/api/backtest': {
      decision_start: '2026-01-01',
      decision_end: '2026-01-01',
      timezone: 'Europe/London',
      first: backtestCutoff('09:00:00'),
      second: backtestCutoff('12:00:00'),
      common: {
        matched_observations: 1,
        first_cutoff_metrics: metrics,
        second_cutoff_metrics: metrics,
      },
      first_cutoff_error_quantiles_mw: { p10: -5, p50: 0, p90: 5 },
      first_cutoff_mean_forecast_mw: 100,
      first_cutoff_matched_observations: 1,
    },
  }
  await route.fulfill({ status: 200, json: responses[path] ?? {} })
}

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

test('all routes render across viewports with accessible navigation and charts', async ({ page }) => {
  await page.route('**/api/**', fulfillApi)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/overview')

  const routes = [
    { label: 'Overview', heading: 'Procurement forecast overview', path: '/overview' },
    { label: 'Forecast explorer', heading: 'Forecast explorer', path: '/forecasts' },
    { label: 'Accuracy analysis', heading: 'Accuracy analysis', path: '/accuracy' },
    { label: 'Historical analysis', heading: 'Historical analysis', path: '/history' },
    { label: 'Backtesting lab', heading: 'Backtesting lab', path: '/backtesting' },
    { label: 'Data & methodology', heading: 'Methodology and data quality', path: '/methodology' },
  ]

  for (const { label, heading, path } of routes) {
    await page.getByRole('link', { name: label }).click()
    await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible()
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: 900 })
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth > 1,
      )
      expect(overflow, `${path} overflows at ${width}px`).toBe(false)
    }
  }

  await page.getByLabel('Decision date period').selectOption('2026-01-01|2026-01-01')
  await expect(page.getByText('Decisions: 2026-01-01 through 2026-01-01')).toBeVisible()
  await page.getByRole('link', { name: 'Overview' }).click()
  await page.keyboard.press('Tab')
  expect(await page.getByRole('link', { name: 'Forecast explorer' }).evaluate((element) =>
    getComputedStyle(element).outlineStyle,
  )).toBe('solid')
  await page.getByRole('link', { name: 'Forecast explorer' }).click()
  await expect(page.getByRole('img', { name: /Line chart comparing forecast and actual/ })).toBeVisible()
  await page.getByRole('link', { name: 'Data & methodology' }).click()
  await expect(page.getByText('Ingestion runs retained')).toBeVisible()

  const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  expect(accessibility.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    description: violation.description,
    nodes: violation.nodes.map((node) => node.target),
  }))).toEqual([])
})
