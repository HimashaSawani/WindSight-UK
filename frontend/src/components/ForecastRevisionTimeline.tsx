import { useState } from 'react'
import { useForecastRevisions } from '../hooks/useAnalytics'
import { getApiErrorMessage } from '../services/api'
import { formatLondonDateTime } from '../utils/dates'
import { ForecastRevisionTimelineChart } from './AnalyticsCharts'
import { EmptyState, ErrorState, LoadingState, Panel } from './DashboardPrimitives'

export function ForecastRevisionTimeline({
  decisionDate,
  targetTimes,
}: {
  decisionDate: string
  targetTimes: string[]
}) {
  const [targetTime, setTargetTime] = useState(targetTimes[0] ?? '')
  const revisions = useForecastRevisions(decisionDate, targetTime)

  return (
    <Panel
      className="mt-5"
      title="Forecast revision timeline"
      subtitle="WINDFOR revisions for one delivery interval, in publication-time order"
    >
      <p className="mb-4 max-w-4xl text-sm leading-6 text-slate-600">
        This visualization shows how wind generation forecasts for a selected delivery interval changed over time. The highlighted forecast is the latest revision available before the procurement decision cutoff.
        {' '}Forecasts published after the cutoff were not available when the historical decision was made.
      </p>
      <label className="mb-5 inline-flex flex-wrap items-center gap-3 text-sm font-medium text-slate-700">
        Delivery interval
        <select
          value={targetTime}
          onChange={(event) => setTargetTime(event.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal"
        >
          {targetTimes.map((target) => (
            <option key={target} value={target}>{formatLondonDateTime(target)} Europe/London</option>
          ))}
        </select>
      </label>
      {revisions.isPending ? (
        <LoadingState label="Loading forecast publication revisions" />
      ) : revisions.isError ? (
        <ErrorState message={getApiErrorMessage(revisions.error)} retry={() => void revisions.refetch()} />
      ) : revisions.data.revisions.length === 0 ? (
        <EmptyState
          title="No forecast revisions available"
          detail="WINDFOR returned no validated forecast revisions for this delivery interval within the configured publication lookback."
        />
      ) : (
        <ForecastRevisionTimelineChart data={revisions.data} />
      )}
    </Panel>
  )
}
