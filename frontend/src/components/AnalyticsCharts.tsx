import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ComparisonObservation, DailyAccuracy, ForecastRevisionResponse } from '../types/api'
import { formatLondonDateTime } from '../utils/dates'

const axisProps = {
  tick: { fontSize: 11, fill: '#64748b' },
  tickLine: false,
  axisLine: false,
}

function LondonTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name?: string; value?: number | null; color?: string }>; label?: string }) {
  if (!active || !payload?.length) return null
  const dateLabel = label ? formatLondonDateTime(label) : ''
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs shadow-lg">
      <p className="mb-2 font-semibold text-slate-700">{dateLabel}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }} className="py-0.5">
          {entry.name}: {entry.value == null ? 'Missing' : `${entry.value.toLocaleString('en-GB', { maximumFractionDigits: 1 })} MW`}
        </p>
      ))}
    </div>
  )
}

export function ComparisonChart({ data }: { data: ComparisonObservation[] }) {
  const hasSeries = data.some((row) => row.forecast_mw !== null || row.actual_mw !== null)
  if (!hasSeries) return <p className="py-10 text-center text-sm text-slate-500">No forecast or actual points are available.</p>
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="target_time" tickFormatter={(value: string) => new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London' }).format(new Date(value))} minTickGap={28} {...axisProps} />
          <YAxis width={58} tickFormatter={(value: number) => value.toLocaleString('en-GB')} {...axisProps} />
          <Tooltip content={<LondonTooltip />} />
          <Legend />
          <Line name="Forecast" dataKey="forecast_mw" stroke="#0f766e" strokeWidth={2.2} dot={false} connectNulls={false} />
          <Line name="Actual" dataKey="actual_mw" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ErrorChart({ data }: { data: ComparisonObservation[] }) {
  const hasErrors = data.some((row) => row.error_mw !== null)
  if (!hasErrors) return <p className="py-10 text-center text-sm text-slate-500">No matched observations are available to calculate interval errors.</p>
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="target_time" tickFormatter={(value: string) => new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London' }).format(new Date(value))} minTickGap={28} {...axisProps} />
          <YAxis width={58} tickFormatter={(value: number) => value.toLocaleString('en-GB')} {...axisProps} />
          <Tooltip content={<LondonTooltip />} />
          <ReferenceLine y={0} stroke="#94a3b8" />
          <Line name="Forecast − actual" dataKey="error_mw" stroke="#d97706" strokeWidth={2} dot={false} connectNulls={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function HistoryTrendChart({ data }: { data: DailyAccuracy[] }) {
  const chartData = data.map(({ decision_date, delivery_date, metrics }) => ({
    target_time: `${decision_date}T12:00:00Z`,
    decision_date,
    delivery_date,
    mae_mw: metrics.mae_mw,
    rmse_mw: metrics.rmse_mw,
    bias_mw: metrics.mean_bias_error_mw,
  }))
  if (!chartData.length || chartData.every((row) => row.mae_mw === null && row.rmse_mw === null && row.bias_mw === null)) {
    return <p className="py-10 text-center text-sm text-slate-500">No matched daily observations are available.</p>
  }
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="target_time" tickFormatter={(value: string) => new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'Europe/London' })} minTickGap={20} {...axisProps} />
          <YAxis width={58} tickFormatter={(value: number) => value.toLocaleString('en-GB')} {...axisProps} />
          <Tooltip content={<LondonTooltip />} />
          <Legend />
          <Line name="MAE (MW)" dataKey="mae_mw" stroke="#0f766e" strokeWidth={2} dot={false} connectNulls={false} />
          <Line name="RMSE (MW)" dataKey="rmse_mw" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls={false} />
          <Line name="Mean bias (MW)" dataKey="bias_mw" stroke="#d97706" strokeWidth={2} dot={false} connectNulls={false} />
          <ReferenceLine y={0} stroke="#cbd5e1" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

interface ForecastRevisionPoint {
  publish_time: string
  published_at_ms: number
  generation_mw: number
  eligible_generation_mw: number | null
  post_decision_generation_mw: number | null
  selected_generation_mw: number | null
  selected_for_decision: boolean
  available_at_decision_time: boolean
  duplicate_publication_timestamp: boolean
  conflicting_duplicate: boolean
}

function ForecastRevisionTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload?: ForecastRevisionPoint }>
}) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null
  return (
    <div className="max-w-xs rounded-lg border border-slate-200 bg-white p-3 text-xs shadow-lg">
      <p className="font-semibold text-slate-700">{formatLondonDateTime(point.publish_time)} Europe/London</p>
      <p className="mt-1 text-slate-600">{point.generation_mw.toLocaleString('en-GB', { maximumFractionDigits: 1 })} MW</p>
      <p className={`mt-1 font-medium ${point.available_at_decision_time ? 'text-teal-700' : 'text-amber-700'}`}>
        {point.selected_for_decision ? 'Selected for decision' : point.available_at_decision_time ? 'Available at decision time' : 'Post-decision revision'}
      </p>
      {point.duplicate_publication_timestamp && (
        <p className="mt-1 text-slate-500">
          Duplicate publication timestamp{point.conflicting_duplicate ? ' with conflicting values' : ''}
        </p>
      )}
    </div>
  )
}

export function ForecastRevisionTimelineChart({ data }: { data: ForecastRevisionResponse }) {
  const chartData: ForecastRevisionPoint[] = data.revisions.map((revision) => ({
    ...revision,
    published_at_ms: new Date(revision.publish_time).getTime(),
    eligible_generation_mw: revision.available_at_decision_time ? revision.generation_mw : null,
    post_decision_generation_mw: revision.available_at_decision_time ? null : revision.generation_mw,
    selected_generation_mw: revision.selected_for_decision ? revision.generation_mw : null,
  }))
  const cutoffMs = new Date(data.decision_cutoff).getTime()
  const timestamps = chartData.map((point) => point.published_at_ms)
  const lowerBound = Math.min(cutoffMs, ...timestamps)
  const upperBound = Math.max(cutoffMs, ...timestamps)
  const padding = Math.max((upperBound - lowerBound) * 0.08, 60_000)

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-600">
        <span>Delivery interval: <strong>{formatLondonDateTime(data.target_time)} Europe/London</strong></span>
        <span>Decision cutoff: <strong>{formatLondonDateTime(data.decision_cutoff)} Europe/London</strong></span>
        {data.revisions.some((revision) => revision.selected_for_decision) && (
          <span className="font-semibold text-teal-700">Highlighted point is the selected forecast</span>
        )}
      </div>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 16, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="published_at_ms"
              type="number"
              scale="time"
              domain={[lowerBound - padding, upperBound + padding]}
              tickFormatter={(value: number) => new Intl.DateTimeFormat('en-GB', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Europe/London',
              }).format(new Date(value))}
              minTickGap={24}
              {...axisProps}
            />
            <YAxis width={58} tickFormatter={(value: number) => value.toLocaleString('en-GB')} {...axisProps} />
            <Tooltip content={<ForecastRevisionTooltip />} />
            <Legend />
            <ReferenceLine
              x={cutoffMs}
              stroke="#dc2626"
              strokeDasharray="5 4"
              label={{ value: 'Decision cutoff', position: 'insideTopRight', fill: '#b91c1c', fontSize: 11 }}
            />
            <Line
              name="Available at decision"
              dataKey="eligible_generation_mw"
              stroke="#0f766e"
              strokeWidth={2.2}
              dot={{ r: 4, fill: '#0f766e' }}
              activeDot={{ r: 6 }}
              connectNulls={false}
            />
            <Line
              name="Post-decision revision"
              dataKey="post_decision_generation_mw"
              stroke="#d97706"
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={{ r: 4, fill: '#d97706' }}
              activeDot={{ r: 6 }}
              connectNulls={false}
            />
            <Line
              name="Selected forecast"
              dataKey="selected_generation_mw"
              stroke="transparent"
              strokeWidth={0}
              dot={{ r: 8, fill: '#0f766e', stroke: '#ffffff', strokeWidth: 2 }}
              activeDot={{ r: 9 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}
