import type { ComparisonObservation } from '../types/api'
import { formatLondonDateTime } from '../utils/dates'

const number = (value: number | null) => value === null ? '—' : value.toLocaleString('en-GB', { maximumFractionDigits: 1 })

export function ComparisonTable({ data }: { data: ComparisonObservation[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[850px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            <th className="px-3 py-3 font-medium">Target (London)</th>
            <th className="px-3 py-3 font-medium">Forecast MW</th>
            <th className="px-3 py-3 font-medium">Actual MW</th>
            <th className="px-3 py-3 font-medium">Error MW</th>
            <th className="px-3 py-3 font-medium">Published (London)</th>
            <th className="px-3 py-3 font-medium">Forecast age</th>
            <th className="px-3 py-3 font-medium">Availability</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.target_time} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
              <td className="whitespace-nowrap px-3 py-3 font-medium text-slate-700">{formatLondonDateTime(row.target_time)}</td>
              <td className="px-3 py-3 tabular-nums">{number(row.forecast_mw)}</td>
              <td className="px-3 py-3 tabular-nums">{number(row.actual_mw)}</td>
              <td className="px-3 py-3 tabular-nums">{number(row.error_mw)}</td>
              <td className="whitespace-nowrap px-3 py-3 text-slate-600">{row.forecast_publish_time ? formatLondonDateTime(row.forecast_publish_time) : '—'}</td>
              <td className="px-3 py-3 text-slate-600">{row.forecast_age_minutes === null ? '—' : `${Math.round(row.forecast_age_minutes)} min`}</td>
              <td className="px-3 py-3">
                <span className={`whitespace-nowrap rounded-full px-2 py-1 text-xs ${row.availability === 'matched' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}>
                  {row.availability.replaceAll('_', ' ')}
                </span>
              </td>
            </tr>
          ))}
          {!data.length && <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500">No delivery intervals returned.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
