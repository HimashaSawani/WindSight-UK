import { AlertCircle, LoaderCircle, RefreshCw, Wind } from 'lucide-react'
import type { ReactNode } from 'react'

export function MetricCard({
  title,
  value,
  unit,
  detail,
  icon,
}: {
  title: string
  value: string
  unit?: string
  detail?: string
  icon?: ReactNode
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <span className="rounded-lg bg-teal-50 p-2 text-teal-700">{icon ?? <Wind size={17} />}</span>
      </div>
      <p className="mt-4 text-2xl font-semibold tabular-nums text-slate-900">
        {value}<span className="ml-1 text-sm font-medium text-slate-500">{unit}</span>
      </p>
      {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
    </article>
  )
}

export function LoadingState({ label = 'Loading Elexon data' }: { label?: string }) {
  return (
    <div role="status" aria-label={label} className="min-h-56 rounded-xl border border-slate-200 bg-white p-5">
      <span className="sr-only">{label}</span>
      <div className="flex items-center gap-2 text-sm text-slate-500"><LoaderCircle className="animate-spin text-teal-700" size={18} />{label}</div>
      <div className="mt-7 animate-pulse space-y-4" aria-hidden="true">
        <div className="h-3 w-1/3 rounded bg-slate-100" />
        <div className="h-32 rounded-lg bg-slate-100" />
        <div className="h-3 w-2/3 rounded bg-slate-100" />
      </div>
    </div>
  )
}

export function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-900">
      <div className="flex items-start gap-3">
        <AlertCircle size={19} className="mt-0.5 shrink-0" />
        <div className="flex-1">
          <p className="font-semibold">Could not load live data</p>
          <p className="mt-1 break-words">{message}</p>
          <button onClick={retry} className="mt-3 inline-flex items-center gap-2 font-semibold underline underline-offset-2">
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      </div>
    </div>
  )
}

export function EmptyState({ title = 'No validated observations', detail }: { title?: string; detail?: string }) {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 text-center">
      <Wind size={24} className="text-slate-400" />
      <p className="mt-3 font-medium text-slate-700">{title}</p>
      <p className="mt-1 max-w-xl text-sm text-slate-500">
        {detail ?? 'Source observations are missing for the selected period. Missing values are not substituted.'}
      </p>
    </div>
  )
}

export function CoverageIndicator({ label, value }: { label: string; value: number | null }) {
  const safeValue = value === null ? 0 : Math.max(0, Math.min(value, 100))
  return (
    <div>
      <div className="mb-2 flex justify-between gap-2 text-sm">
        <span className="text-slate-600">{label}</span>
        <span className="font-semibold tabular-nums text-slate-800">{value === null ? '—' : `${value.toFixed(1)}%`}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-teal-600 transition-[width]" style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  )
}

export function Panel({ title, subtitle, children, className = '' }: { title: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      <div className="mb-4">
        <h2 className="font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </section>
  )
}

export function PageTitle({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="mb-6">
      <p className="text-sm font-semibold text-teal-700">{eyebrow}</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
    </div>
  )
}
