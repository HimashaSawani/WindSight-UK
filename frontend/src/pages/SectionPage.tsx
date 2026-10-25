import { useAccuracy, useApiPerformance, useComparison, useDataQuality, useHistory, useOverview } from '../hooks/useAnalytics'
import { useDecisionPeriod } from '../hooks/useDecisionPeriod'
import { getDecisionDates } from '../utils/decisionDates'
import { formatLondonDateTime } from '../utils/dates'
import { ComparisonChart, ErrorChart, HistoryTrendChart } from '../components/AnalyticsCharts'
import { ComparisonTable } from '../components/ComparisonTable'
import { ForecastRevisionTimeline } from '../components/ForecastRevisionTimeline'
import { CoverageIndicator, EmptyState, ErrorState, LoadingState, MetricCard, PageTitle, Panel } from '../components/DashboardPrimitives'
import { getApiErrorMessage } from '../services/api'

const value = (number: number | null) => number === null ? '—' : number.toLocaleString('en-GB', { maximumFractionDigits: 2 })

export function ForecastExplorerPage() {
  const period = useDecisionPeriod()
  const selectedDate = period.start
  const comparison = useComparison(selectedDate, selectedDate, selectedDate)
  const accuracy = useAccuracy(selectedDate, selectedDate, selectedDate)
  const first = comparison.data?.observations[0]
  const rows = comparison.data?.observations ?? []
  const setSelected = (newDate: string) => period.setSingleDate(newDate)

  return (
    <section>
      <PageTitle eyebrow="Interval-level view" title="Forecast explorer" description="Inspect selected forecasts, publication timestamps, forecast age, and actual-data availability for one decision date." />
      <div className="mb-5 flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white p-4">
        <label className="text-sm font-medium text-slate-700">Decision date
          <select value={selectedDate} onChange={(event) => setSelected(event.target.value)} className="ml-3 rounded-lg border border-slate-200 px-3 py-2 text-sm">
            {getDecisionDates('2026-01-01', '2026-01-31').map((date) => <option key={date} value={date}>{date}</option>)}
          </select>
        </label>
        <span className="text-sm text-slate-600">Delivery date: <strong>{first?.delivery_date ?? '—'}</strong></span>
        <span className="text-sm text-slate-600">Decision cutoff: <strong>{comparison.data?.decision_cutoff_local_time ?? '—'} Europe/London</strong></span>
      </div>
      {comparison.isPending ? <LoadingState /> : comparison.isError ? <ErrorState message={getApiErrorMessage(comparison.error)} retry={() => void comparison.refetch()} /> : rows.length === 0 ? <EmptyState /> : (
        <>
          <Panel title="Selected forecast and actual" subtitle={`${rows.length} expected delivery intervals; lines stop at missing observations`}>
            <ComparisonChart data={rows} />
          </Panel>
          <ForecastRevisionTimeline
            key={selectedDate}
            decisionDate={selectedDate}
            targetTimes={rows.map((row) => row.target_time)}
          />
          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <Panel title="Forecast availability">{accuracy.isPending ? <LoadingState label="Loading backend coverage" /> : accuracy.isError ? <ErrorState message={getApiErrorMessage(accuracy.error)} retry={() => void accuracy.refetch()} /> : <CoverageIndicator label="Forecast intervals with a selected value" value={accuracy.data.overall.forecast_coverage_pct} />}</Panel>
            <Panel title="Selection details" subtitle="Publication timestamp must be at or before the displayed decision cutoff">
              <p className="text-sm leading-6 text-slate-600">The forecast age is calculated from publication time to the decision cutoff. Missing forecasts remain blank; actuals are not replaced with zero.</p>
            </Panel>
          </div>
          <Panel className="mt-5" title="Delivery intervals" subtitle="Target and publication timestamps are presented in Europe/London; source values remain MW">
            <ComparisonTable data={rows} />
          </Panel>
        </>
      )}
    </section>
  )
}

export function AccuracyAnalysisPage() {
  const { start, end } = useDecisionPeriod()
  const accuracy = useAccuracy(start, end)
  const comparison = useComparison(start, end)
  if (accuracy.isPending) return <LoadingState label="Calculating matched-observation accuracy" />
  if (accuracy.isError) return <ErrorState message={getApiErrorMessage(accuracy.error)} retry={() => void accuracy.refetch()} />
  const metrics = accuracy.data.overall
  const matched = comparison.data?.observations.filter((row) => row.error_mw !== null) ?? []
  return (
    <section>
      <PageTitle eyebrow="Matched observations only" title="Accuracy analysis" description="Error is forecast minus actual: positive values indicate overestimation; negative values indicate underestimation." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard title="MAE" value={value(metrics.mae_mw)} unit="MW" />
        <MetricCard title="RMSE" value={value(metrics.rmse_mw)} unit="MW" />
        <MetricCard title="Mean bias error" value={value(metrics.mean_bias_error_mw)} unit="MW" detail="Positive = overestimate" />
        <MetricCard title="WAPE" value={value(metrics.wape_pct)} unit={metrics.wape_pct === null ? '' : '%'} detail="Undefined when total actual magnitude is zero" />
        <MetricCard title="Matched intervals" value={metrics.matched_observations.toLocaleString('en-GB')} detail={`of ${metrics.observation_count.toLocaleString()} expected`} />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Panel title="Forecast vs actual" subtitle="Matched and available observations; no interpolation">
          {comparison.isPending ? <LoadingState /> : comparison.isError ? <ErrorState message={getApiErrorMessage(comparison.error)} retry={() => void comparison.refetch()} /> : matched.length ? <ComparisonChart data={matched} /> : <EmptyState />}
        </Panel>
        <Panel title="Forecast error" subtitle="Forecast − actual (MW), matched intervals only">
          {comparison.isPending ? <LoadingState /> : comparison.isError ? <ErrorState message={getApiErrorMessage(comparison.error)} retry={() => void comparison.refetch()} /> : <ErrorChart data={comparison.data.observations} />}
        </Panel>
      </div>
      <Panel className="mt-5" title="Daily error breakdown" subtitle="Daily metrics are calculated by the backend from matched observations">
        <AccuracyDailyTable data={accuracy.data.by_decision_date} />
      </Panel>
      <Panel className="mt-5" title="Missing-data treatment">
        <p className="text-sm leading-6 text-slate-600">Intervals missing either forecast or actual are excluded from MAE, RMSE, bias, and WAPE numerators and denominators. Forecast and actual coverage are reported against expected target intervals. Zero actual generation is retained; WAPE is undefined when the sum of absolute matched actuals is zero.</p>
      </Panel>
    </section>
  )
}

export function HistoricalAnalysisPage() {
  const { start, end } = useDecisionPeriod()
  const history = useHistory(start, end)
  if (history.isPending) return <LoadingState label="Loading historical daily metrics" />
  if (history.isError) return <ErrorState message={getApiErrorMessage(history.error)} retry={() => void history.refetch()} />
  return (
    <section>
      <PageTitle eyebrow="Decision-date history" title="Historical analysis" description={`Daily forecast accuracy for decisions from ${start} through ${end}. Each decision date evaluates the following delivery date.`} />
      <Panel title="Daily MAE, RMSE and bias" subtitle="Errors are in MW; positive bias means forecast overestimation">
        <HistoryTrendChart data={history.data.days} />
      </Panel>
      <Panel className="mt-5" title="Accuracy comparison" subtitle="All metrics and coverage values are supplied by the backend">
        <AccuracyDailyTable data={history.data.days} />
      </Panel>
    </section>
  )
}

function AccuracyDailyTable({ data }: { data: import('../types/api').DailyAccuracy[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead><tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="px-3 py-3 font-medium">Decision date</th><th className="px-3 py-3 font-medium">Delivery date</th><th className="px-3 py-3 font-medium">Matched</th><th className="px-3 py-3 font-medium">MAE MW</th><th className="px-3 py-3 font-medium">RMSE MW</th><th className="px-3 py-3 font-medium">Bias MW</th><th className="px-3 py-3 font-medium">WAPE</th><th className="px-3 py-3 font-medium">Forecast / actual coverage</th>
        </tr></thead>
        <tbody>{data.map((day) => <tr key={day.decision_date} className="border-b border-slate-100 last:border-0">
          <td className="px-3 py-3">{day.decision_date}</td><td className="px-3 py-3">{day.delivery_date}</td><td className="px-3 py-3">{day.metrics.matched_observations}/{day.metrics.observation_count}</td><td className="px-3 py-3">{value(day.metrics.mae_mw)}</td><td className="px-3 py-3">{value(day.metrics.rmse_mw)}</td><td className="px-3 py-3">{value(day.metrics.mean_bias_error_mw)}</td><td className="px-3 py-3">{day.metrics.wape_pct === null ? '—' : `${value(day.metrics.wape_pct)}%`}</td><td className="px-3 py-3">{day.metrics.forecast_coverage_pct === null ? '—' : `${day.metrics.forecast_coverage_pct.toFixed(1)}%`} / {day.metrics.actual_coverage_pct === null ? '—' : `${day.metrics.actual_coverage_pct.toFixed(1)}%`}</td>
        </tr>)}{data.length === 0 && <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">No daily records returned.</td></tr>}</tbody>
      </table>
    </div>
  )
}

export function MethodologyPage() {
  const { start, end } = useDecisionPeriod()
  const overview = useOverview(start, end)
  const quality = useDataQuality()
  const performance = useApiPerformance()
  const cutoff = overview.data?.decision_cutoff_local_time
  const dateRecords = [
    ['FUELHH', 'Actual half-hourly generation outturn, filtered to fuelType WIND.'],
    ['WINDFOR', 'Wind generation forecast records; source publication times are preserved.'],
  ]
  const ingestionRuns = quality.data?.recent_ingestion_runs ?? []
  const latestIngestionRun = ingestionRuns.at(-1)
  const archiveSize = typeof quality.data?.stored_size_bytes === 'number'
    ? `${quality.data.stored_size_bytes.toLocaleString('en-GB')} bytes`
    : 'Not reported by this API version'
  return (
    <section>
      <PageTitle eyebrow="Source, definitions & coverage" title="Methodology and data quality" description="Transparent source provenance and limitations for historical procurement decision support." />
      {overview.isError && <ErrorState message={getApiErrorMessage(overview.error)} retry={() => void overview.refetch()} />}
      {quality.isError && <div className="mt-4"><ErrorState message={getApiErrorMessage(quality.error)} retry={() => void quality.refetch()} /></div>}
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Elexon BMRS data sources">
          <ul className="space-y-3 text-sm leading-6 text-slate-600">{dateRecords.map(([name, text]) => <li key={name}><strong className="text-slate-800">{name}</strong> — {text}</li>)}</ul>
          <p className="mt-4 text-sm text-slate-500">Data is fetched from Elexon BMRS only. No weather, price, demand or external datasets are used.</p>
        </Panel>
        <Panel title="Point-in-time selection">
          {overview.isPending ? <LoadingState label="Loading configured decision cutoff" /> : <p className="text-sm leading-6 text-slate-600">For each decision date, the delivery date is the following local date. Forecast revisions are eligible only when <code>publishTime ≤ decision cutoff</code>; the latest eligible publication is selected. Configured cutoff: <strong>{cutoff ?? 'unavailable'} Europe/London</strong>. This is a configurable analysis assumption, not an asserted market gate closure.</p>}
        </Panel>
      </div>
      <Panel className="mt-5" title="Metric definitions">
        <ul className="grid gap-3 text-sm leading-6 text-slate-600 sm:grid-cols-2">
          <li><strong>MAE</strong> — mean absolute error over matched intervals.</li>
          <li><strong>RMSE</strong> — square root of mean squared error over matched intervals.</li>
          <li><strong>Mean bias</strong> — forecast − actual; positive means overestimation.</li>
          <li><strong>WAPE</strong> — total absolute error divided by total absolute actual generation × 100; undefined at zero denominator.</li>
          <li><strong>Coverage</strong> — records available divided by expected delivery intervals.</li>
          <li>All error metrics use matched forecast/actual observations only.</li>
        </ul>
      </Panel>
      <Panel className="mt-5" title="Missing data and comparability limitation">
        <p className="text-sm leading-6 text-slate-600">Missing forecasts and missing actuals remain null and count against their respective coverage. They are never replaced with zero. FUELHH is documented as average MW over 30-minute intervals. WINDFOR documents generation forecasts but available endpoint documentation does not confirm equivalent measurement semantics; observed WINDFOR target times are hourly. Comparisons use exact timestamps only: no half-hour interpolation, forward-fill, or MWh conversion is applied. Treat results as indicative until Elexon confirms compatible definitions.</p>
      </Panel>
      <Panel className="mt-5" title="Retrieval diagnostics">
        {quality.isPending ? <LoadingState label="Loading data-quality status" /> : quality.isError ? <p className="text-sm text-rose-700">Diagnostics are unavailable.</p> : <>
        <p className="mb-4 text-sm leading-6 text-slate-600">Analysis data source: <strong>{quality.data.analytics_data_source === 'live_elexon' ? 'live Elexon API' : quality.data.analytics_data_source}</strong>. The persisted records below are an independent ingestion archive and are not currently used by analysis endpoints.</p>
        <div className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><p className="text-slate-500">Pipeline status / operation</p><p className="mt-1 font-semibold">{quality.data.status} / {quality.data.last_operation ?? 'none'}</p></div>
          <div><p className="text-slate-500">Last attempted sync</p><p className="mt-1 font-semibold">{quality.data.last_attempt ? formatLondonDateTime(quality.data.last_attempt) : 'Not recorded'}</p></div>
          <div><p className="text-slate-500">Last successful sync</p><p className="mt-1 font-semibold">{quality.data.last_successful_refresh ? formatLondonDateTime(quality.data.last_successful_refresh) : 'Not recorded'}</p></div>
          <div><p className="text-slate-500">Elexon failed requests</p><p className="mt-1 font-semibold">{quality.data.failed_requests}</p></div>
          <div><p className="text-slate-500">Malformed records · forecasts / actuals</p><p className="mt-1 font-semibold">{quality.data.invalid_forecast_records} / {quality.data.invalid_actual_records}</p></div>
          <div><p className="text-slate-500">Missing forecast / actual intervals</p><p className="mt-1 font-semibold">{quality.data.missing_forecast_records} / {quality.data.missing_actual_records}</p></div>
          <div><p className="text-slate-500">Elexon source latest · forecast</p><p className="mt-1 font-semibold">{quality.data.forecast_source_latest_time ? formatLondonDateTime(quality.data.forecast_source_latest_time) : 'Not recorded'}</p></div>
          <div><p className="text-slate-500">Elexon source latest · actual</p><p className="mt-1 font-semibold">{quality.data.actual_source_latest_time ? formatLondonDateTime(quality.data.actual_source_latest_time) : 'Not recorded'}</p></div>
          <div><p className="text-slate-500">Cache hit ratio</p><p className="mt-1 font-semibold">{quality.data.cache_hits + quality.data.requests_made ? `${(quality.data.cache_hits / (quality.data.cache_hits + quality.data.requests_made) * 100).toFixed(1)}%` : '—'}</p></div>
          <div><p className="text-slate-500">Automated sync</p><p className="mt-1 font-semibold">{quality.data.ingestion_enabled ? 'Enabled' : 'Disabled'}</p></div>
          <div><p className="text-slate-500">Persisted source records · forecasts / actuals</p><p className="mt-1 font-semibold">{quality.data.stored_forecast_records} / {quality.data.stored_actual_records}</p></div>
          <div><p className="text-slate-500">Ingestion archive size</p><p className="mt-1 font-semibold">{archiveSize}</p></div>
          <div><p className="text-slate-500">Rejected / duplicate source records</p><p className="mt-1 font-semibold">{quality.data.stored_rejected_records} / {quality.data.duplicate_forecast_records + quality.data.duplicate_actual_records}</p></div>
          <div><p className="text-slate-500">Conflicting groups · forecast / actual</p><p className="mt-1 font-semibold">{quality.data.conflicting_forecast_groups} / {quality.data.conflicting_actual_groups}</p></div>
          <div><p className="text-slate-500">Missing actual intervals</p><p className="mt-1 font-semibold">{quality.data.missing_actual_intervals}</p></div>
          <div><p className="text-slate-500">Off-grid forecast timestamps</p><p className="mt-1 font-semibold">{quality.data.off_grid_forecast_records}</p></div>
          <div><p className="text-slate-500">Ingestion runs retained</p><p className="mt-1 font-semibold">{ingestionRuns.length} (last 10 shown)</p></div>
          <div className="sm:col-span-2"><p className="text-slate-500">Pipeline detail</p><p className="mt-1 font-medium">{quality.data.message}</p></div>
        </div>
        </>}
        {!quality.isPending && !quality.isError && latestIngestionRun && (
            <div className="mt-4 rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-semibold">Latest automated/manual sync run · {latestIngestionRun.status}</h3>
              <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div><dt className="text-slate-500">Retrieved · forecast / actual</dt><dd className="font-medium">{latestIngestionRun.forecast_records_retrieved} / {latestIngestionRun.actual_records_retrieved}</dd></div>
                <div><dt className="text-slate-500">Valid · forecast / actual</dt><dd className="font-medium">{latestIngestionRun.forecast_records_valid} / {latestIngestionRun.actual_records_valid}</dd></div>
                <div><dt className="text-slate-500">Rejected records</dt><dd className="font-medium">{latestIngestionRun.rejected_records}</dd></div>
                <div><dt className="text-slate-500">Exact duplicates · forecast / actual</dt><dd className="font-medium">{latestIngestionRun.duplicate_forecast_records} / {latestIngestionRun.duplicate_actual_records}</dd></div>
                <div><dt className="text-slate-500">Missing actual intervals</dt><dd className="font-medium">{latestIngestionRun.missing_actual_intervals}</dd></div>
                <div><dt className="text-slate-500">Source request errors</dt><dd className="font-medium">{latestIngestionRun.failed_requests}</dd></div>
                <div><dt className="text-slate-500">Forecast source latest</dt><dd className="font-medium">{latestIngestionRun.forecast_source_latest_time ? formatLondonDateTime(latestIngestionRun.forecast_source_latest_time) : 'No valid records'}</dd></div>
                <div><dt className="text-slate-500">Actual source latest</dt><dd className="font-medium">{latestIngestionRun.actual_source_latest_time ? formatLondonDateTime(latestIngestionRun.actual_source_latest_time) : 'No valid records'}</dd></div>
              </dl>
              {latestIngestionRun.error && <p role="alert" className="mt-3 text-sm text-rose-700">Pipeline failure: {latestIngestionRun.error}</p>}
            </div>
        )}
        <p className="mt-3 text-xs leading-5 text-slate-500">Elexon HTTP/cache counters are process-local since backend startup; persisted source records and ingestion runs survive container recreation. Missing intervals describe source-data availability and do not, by themselves, mean the pipeline failed. “Source latest” is the newest timestamp in that sync, not a claim that historical source data is current.</p>
      </Panel>
      <Panel className="mt-5" title="API performance" subtitle="Rolling five-minute window, retaining up to 10,000 recent requests; metrics reset when the API process restarts.">
        {performance.isPending ? <LoadingState label="Loading API performance metrics" /> : performance.isError ? <ErrorState message={getApiErrorMessage(performance.error)} retry={() => void performance.refetch()} /> : (
          <div className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div><p className="text-slate-500">API availability</p><p className="mt-1 text-lg font-semibold">{performance.data.availability_pct === null ? 'No requests yet' : `${performance.data.availability_pct.toFixed(2)}%`}</p></div>
            <div><p className="text-slate-500">Mean response time</p><p className="mt-1 text-lg font-semibold">{performance.data.mean_response_time_ms === null ? '—' : `${performance.data.mean_response_time_ms.toFixed(1)} ms`}</p></div>
            <div><p className="text-slate-500">P95 response time</p><p className="mt-1 text-lg font-semibold">{performance.data.p95_response_time_ms === null ? '—' : `${performance.data.p95_response_time_ms.toFixed(1)} ms`}</p></div>
            <div><p className="text-slate-500">Requests / server errors (5m)</p><p className="mt-1 text-lg font-semibold">{performance.data.requests_in_window} / {performance.data.server_errors_in_window}</p></div>
            <div><p className="text-slate-500">Process uptime</p><p className="mt-1 font-semibold">{Math.floor(performance.data.uptime_seconds / 3600)}h {Math.floor(performance.data.uptime_seconds % 3600 / 60)}m</p></div>
            <div><p className="text-slate-500">Lifetime requests / errors</p><p className="mt-1 font-semibold">{performance.data.total_requests} / {performance.data.total_server_errors}</p></div>
          </div>
        )}
      </Panel>
    </section>
  )
}
