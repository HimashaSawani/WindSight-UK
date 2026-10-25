import { Activity, Clock3, Gauge, Wind } from 'lucide-react'
import { useAccuracy, useComparison, useDataQuality, useOverview } from '../hooks/useAnalytics'
import { useDecisionPeriod } from '../hooks/useDecisionPeriod'
import { formatLondonDateTime } from '../utils/dates'
import { ComparisonChart, HistoryTrendChart } from '../components/AnalyticsCharts'
import { CoverageIndicator, EmptyState, ErrorState, LoadingState, MetricCard, PageTitle, Panel } from '../components/DashboardPrimitives'
import { getApiErrorMessage } from '../services/api'

const formatMw = (value: number | null) => value === null ? '—' : value.toLocaleString('en-GB', { maximumFractionDigits: 1 })
const formatMetric = (value: number | null) => value === null ? '—' : value.toLocaleString('en-GB', { maximumFractionDigits: 2 })

export function OverviewPage() {
  const { start, end } = useDecisionPeriod()
  const overview = useOverview(start, end)
  const accuracy = useAccuracy(start, end)
  const comparison = useComparison(start, end)
  const quality = useDataQuality()

  if (overview.isPending) return <LoadingState label="Retrieving January decision and delivery data from Elexon BMRS" />
  if (overview.isError) return <ErrorState message={getApiErrorMessage(overview.error)} retry={() => void overview.refetch()} />
  const metrics = overview.data.metrics
  const loadingMore = comparison.isPending || accuracy.isPending
  const errorMore = comparison.error ?? accuracy.error

  return (
    <section>
      <PageTitle
        eyebrow="Day-Ahead Wind Forecast Intelligence"
        title="Procurement forecast overview"
        description="Monitor the forecast available at each selected decision cutoff and assess it against actual wind generation on the following delivery date."
      />
      <div className="mb-5 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-teal-100 bg-teal-50/70 px-4 py-3 text-sm text-teal-950">
        <span className="inline-flex items-center gap-2 font-medium"><Clock3 size={16} /> Decision cutoff: {overview.data.decision_cutoff_local_time} Europe/London</span>
        <span className="text-teal-900">Decision date and delivery date are separate; delivery is the next local calendar day.</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard title="Avg forecast generation" value={formatMw(metrics.mean_forecast_mw)} unit="MW" icon={<Wind size={17} />} detail="Available forecasts" />
        <MetricCard title="Avg actual generation" value={formatMw(metrics.mean_actual_mw)} unit="MW" icon={<Activity size={17} />} detail="Available actual observations" />
        <MetricCard title="Mean absolute error" value={formatMetric(metrics.mae_mw)} unit="MW" icon={<Gauge size={17} />} />
        <MetricCard title="Root mean squared error" value={formatMetric(metrics.rmse_mw)} unit="MW" />
        <MetricCard title="Mean bias error" value={formatMetric(metrics.mean_bias_error_mw)} unit="MW" detail="Positive = overforecast" />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(260px,0.75fr)]">
        <Panel title="Forecast vs actual generation" subtitle="MW at exact matched target timestamps">
          {comparison.isPending ? <LoadingState /> : comparison.isError ? <ErrorState message={getApiErrorMessage(comparison.error)} retry={() => void comparison.refetch()} /> : comparison.data.observations.length ? <ComparisonChart data={comparison.data.observations} /> : <EmptyState />}
        </Panel>
        <Panel title="Data coverage" subtitle={`${metrics.matched_observations.toLocaleString()} matched intervals of ${metrics.observation_count.toLocaleString()} expected`}>
          <div className="space-y-6 pt-2">
            <CoverageIndicator label="Forecast availability" value={metrics.forecast_coverage_pct} />
            <CoverageIndicator label="Actual availability" value={metrics.actual_coverage_pct} />
            <div className="grid grid-cols-2 gap-3 border-t border-slate-100 pt-4 text-sm">
              <div><p className="text-slate-500">Missing forecasts</p><p className="mt-1 font-semibold">{metrics.missing_forecasts}</p></div>
              <div><p className="text-slate-500">Missing actuals</p><p className="mt-1 font-semibold">{metrics.missing_actuals}</p></div>
            </div>
          </div>
        </Panel>
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(300px,0.8fr)]">
        <Panel title="Daily accuracy trend" subtitle="Metrics use matched observations only">
          {accuracy.isPending ? <LoadingState /> : accuracy.isError ? <ErrorState message={getApiErrorMessage(accuracy.error)} retry={() => void accuracy.refetch()} /> : <HistoryTrendChart data={accuracy.data.by_decision_date} />}
        </Panel>
        <Panel title="Data source status" subtitle="Elexon BMRS · FUELHH and WINDFOR">
          {quality.isPending ? <LoadingState label="Checking retrieval status" /> : quality.isError ? <ErrorState message={getApiErrorMessage(quality.error)} retry={() => void quality.refetch()} /> : (
            <div className="space-y-4 text-sm">
              <div className="flex items-center justify-between gap-2"><span className="text-slate-500">Retrieval status</span><span className={`rounded-full px-2 py-1 text-xs font-medium ${quality.data.status === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-700'}`}>{quality.data.status.replaceAll('_', ' ')}</span></div>
              <div><p className="text-slate-500">Last successful retrieval</p><p className="mt-1 font-medium">{quality.data.last_successful_refresh ? formatLondonDateTime(quality.data.last_successful_refresh) : 'No successful retrieval recorded yet'}</p></div>
              <div className="grid grid-cols-2 gap-3 border-t border-slate-100 pt-4">
                <div><p className="text-slate-500">WINDFOR normalized</p><p className="font-semibold">{quality.data.normalized_forecast_records.toLocaleString()}</p></div>
                <div><p className="text-slate-500">FUELHH normalized</p><p className="font-semibold">{quality.data.normalized_actual_records.toLocaleString()}</p></div>
              </div>
              <p className="text-xs leading-5 text-slate-500">{quality.data.message}</p>
            </div>
          )}
        </Panel>
      </div>
      {errorMore && <p className="mt-4 text-sm text-amber-800">Some overview panels could not be loaded: {getApiErrorMessage(errorMore)}</p>}
      {loadingMore && <p className="mt-4 text-xs text-slate-500">Loading remaining analysis panels…</p>}
    </section>
  )
}
