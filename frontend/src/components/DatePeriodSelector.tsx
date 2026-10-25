import { CalendarDays } from 'lucide-react'
import { useDecisionPeriod } from '../hooks/useDecisionPeriod'
import { getDecisionDates } from '../utils/decisionDates'

export function DatePeriodSelector() {
  const { start, end, setRange } = useDecisionPeriod()
  const dates = getDecisionDates('2026-01-01', '2026-01-31')
  const allSelected = start === '2026-01-01' && end === '2026-01-31'
  const selected = allSelected ? 'all' : `${start}|${end}`
  const change = (value: string) => {
    if (value === 'all') {
      setRange({ start: '2026-01-01', end: '2026-01-31' })
    } else {
      const [newStart, newEnd] = value.split('|')
      if (newStart && newEnd) setRange({ start: newStart, end: newEnd })
    }
  }

  return (
    <label className="flex items-center gap-2 text-xs text-slate-500">
      <CalendarDays size={15} aria-hidden="true" />
      <span className="sr-only">Decision date period</span>
      <select
        value={selected}
        onChange={(event) => change(event.target.value)}
        className="max-w-52 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm font-medium text-slate-700 outline-none focus:border-teal-600"
      >
        <option value="all">All January 2026</option>
        {dates.map((date) => (
          <option key={date} value={`${date}|${date}`}>{new Date(`${date}T12:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })} decision</option>
        ))}
      </select>
    </label>
  )
}
