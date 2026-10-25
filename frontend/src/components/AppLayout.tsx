import { NavLink, Outlet } from 'react-router-dom'
import { Activity, BarChart3, ClipboardList, Clock3, Info, Wind } from 'lucide-react'
import { useApiHealth } from '../hooks/useApiHealth'
import { DatePeriodSelector } from './DatePeriodSelector'
import { useDecisionPeriod } from '../hooks/useDecisionPeriod'

const navigation = [
  { to: '/overview', label: 'Overview', icon: Activity },
  { to: '/forecasts', label: 'Forecast explorer', icon: Wind },
  { to: '/accuracy', label: 'Accuracy analysis', icon: BarChart3 },
  { to: '/history', label: 'Historical analysis', icon: ClipboardList },
  { to: '/backtesting', label: 'Backtesting lab', icon: Clock3 },
  { to: '/methodology', label: 'Data & methodology', icon: Info },
]

export function AppLayout() {
  const health = useApiHealth()
  const { start, end } = useDecisionPeriod()

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 md:flex">
      <aside className="border-b border-slate-200 bg-[#10233f] text-white md:min-h-screen md:w-64 md:border-b-0 md:border-r">
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="rounded-lg bg-teal-500/15 p-2 text-teal-300"><Wind size={22} /></div>
          <div>
            <p className="font-semibold tracking-wide">WindSight UK</p>
            <p className="text-xs text-slate-400">Forecast intelligence</p>
          </div>
        </div>
        <nav aria-label="Main navigation" className="flex gap-1 overflow-x-auto px-3 pb-3 md:block md:space-y-1">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm ${
                  isActive ? 'bg-white/10 font-medium text-white' : 'text-slate-300 hover:bg-white/5'
                } focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-300`
              }
            >
              <Icon size={17} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden px-5 py-4 text-xs text-slate-400 md:block">
          Decision support only · Not a trading platform
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
          <div>
            <p className="text-sm font-semibold">UK wind generation</p>
            <p className="text-xs text-slate-500">Decisions: {start} through {end}</p>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <DatePeriodSelector />
            <div className="flex items-center gap-2 text-xs">
              <span className={`size-2 rounded-full ${health.isSuccess ? 'bg-emerald-500' : health.isError ? 'bg-rose-500' : 'bg-slate-300'}`} />
              <span className="text-slate-600">
                {health.isPending ? 'Checking API' : health.isSuccess ? 'API connected' : 'API unavailable'}
              </span>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl p-5 sm:p-8">
          <Outlet />
          <footer className="mt-10 border-t border-slate-200 pt-5 text-xs leading-5 text-slate-500">
            Data source: Elexon BMRS · Timestamps stored in UTC and shown in Europe/London.
            No forecast is selected unless its publication time is at or before the decision cutoff.
          </footer>
        </main>
      </div>
    </div>
  )
}
