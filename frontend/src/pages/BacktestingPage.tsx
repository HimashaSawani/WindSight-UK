import { useState, type FormEvent } from 'react'
import { useBacktest } from '../hooks/useAnalytics'
import { useDecisionPeriod } from '../hooks/useDecisionPeriod'
import { getApiErrorMessage } from '../services/api'
import { ErrorState, LoadingState, PageTitle, Panel } from '../components/DashboardPrimitives'

const metric = (value: number | null) => value === null
  ? '—'
  : value.toLocaleString('en-GB', { maximumFractionDigits: 2 })

export function BacktestingPage() {
  const { start, end } = useDecisionPeriod()
  const [firstCutoff, setFirstCutoff] = useState('09:00')
  const [secondCutoff, setSecondCutoff] = useState('12:00')
  const [draftFirst, setDraftFirst] = useState(firstCutoff)
  const [draftSecond, setDraftSecond] = useState(secondCutoff)
  const [scenarioForecast, setScenarioForecast] = useState<number | null>(null)
  const [cutoffError, setCutoffError] = useState('')
  const backtest = useBacktest(start, end, firstCutoff, secondCutoff)
  const data = backtest.data

  function applyCutoffs(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (draftFirst === draftSecond) {
      setCutoffError('Choose two different cutoff times.')
      return
    }
    setCutoffError('')
    setFirstCutoff(draftFirst)
    setSecondCutoff(draftSecond)
  }

  const baselineRows = data ? [data.first, data.second] : []
  const referenceForecast = scenarioForecast ?? data?.first_cutoff_mean_forecast_mw ?? null
  const errors = data?.first_cutoff_error_quantiles_mw
  const outcomes = errors && referenceForecast !== null
    ? [
        { label: 'P10 · lower outcome', mw: Math.max(0, referenceForecast - errors.p90) },
        { label: 'P50 · median outcome', mw: Math.max(0, referenceForecast - errors.p50) },
        { label: 'P90 · higher outcome', mw: Math.max(0, referenceForecast - errors.p10) },
      ]
    : []

  return (
    <section>
      <PageTitle
        eyebrow="Historical point-in-time evaluation"
        title="Backtesting lab"
        description={`Reconstruct forecasts available by two decision cutoffs for ${start} through ${end}. Later publications are excluded from each historical decision.`}
      />

      <Panel title="Choose decision cutoffs" subtitle="Times are interpreted in Europe/London, including daylight-saving rules.">
        <form onSubmit={applyCutoffs} className="flex flex-wrap items-end gap-4">
          <label className="grid gap-1 text-sm font-medium text-slate-700">
            First cutoff
            <input type="time" value={draftFirst} onChange={(event) => setDraftFirst(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm font-medium text-slate-700">
            Second cutoff
            <input type="time" value={draftSecond} onChange={(event) => setDraftSecond(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2" />
          </label>
          <button type="submit" className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800">Run backtest</button>
          {cutoffError && <p role="alert" className="w-full text-sm text-rose-700">{cutoffError}</p>}
        </form>
      </Panel>

      <div className="mt-5">
        {backtest.isPending ? <LoadingState label="Reconstructing cutoff-specific forecasts and benchmarks" /> : backtest.isError ? (
          <ErrorState message={getApiErrorMessage(backtest.error)} retry={() => void backtest.refetch()} />
        ) : data ? (
          <>
            <Panel title="Forecast performance benchmark" subtitle="Persistence baseline = the latest preceding 30-minute interval forecast published by each cutoff. Elexon and baseline scores use the same intervals with a valid preceding forecast.">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[680px] text-left text-sm">
                  <thead><tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-3 font-medium">Decision cutoff</th>
                    <th className="px-3 py-3 font-medium">Elexon MAE</th>
                    <th className="px-3 py-3 font-medium">Persistence MAE</th>
                    <th className="px-3 py-3 font-medium">Elexon RMSE</th>
                    <th className="px-3 py-3 font-medium">Scored intervals</th>
                  </tr></thead>
                  <tbody>{baselineRows.map((result) => <tr key={result.cutoff_local_time} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-3 font-medium">{result.cutoff_local_time.slice(0, 5)} UK time</td>
                    <td className="px-3 py-3">{metric(result.benchmark_forecast_metrics.mae_mw)} MW</td>
                    <td className="px-3 py-3">{metric(result.persistence_metrics.mae_mw)} MW</td>
                    <td className="px-3 py-3">{metric(result.forecast_metrics.rmse_mw)} MW</td>
                    <td className="px-3 py-3">{result.persistence_matched_observations} / {result.forecast_metrics.matched_observations} shared / total</td>
                  </tr>)}</tbody>
                </table>
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-500">The persistence baseline is available only when the preceding delivery interval has a forecast. Benchmark metrics are compared on the shared forecast/baseline subset; Elexon total matched count is also shown. Missing baseline values are never filled or interpolated.</p>
            </Panel>

            <Panel className="mt-5" title="Cutoff comparison on common intervals" subtitle="Both cutoffs are scored on exactly the same delivery timestamps where actuals and both forecasts are present.">
              <p className="mb-4 text-sm text-slate-600">Common matched intervals: <strong>{data.common.matched_observations.toLocaleString('en-GB')}</strong></p>
              <div className="grid gap-4 sm:grid-cols-2">
                {[data.first, data.second].map((cutoff, index) => {
                  const metrics = index === 0 ? data.common.first_cutoff_metrics : data.common.second_cutoff_metrics
                  return (
                    <div key={cutoff.cutoff_local_time} className="rounded-lg border border-slate-200 p-4">
                      <h3 className="font-semibold">{cutoff.cutoff_local_time.slice(0, 5)} UK time</h3>
                      <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
                        <div><dt className="text-slate-500">MAE</dt><dd className="font-semibold">{metric(metrics.mae_mw)} MW</dd></div>
                        <div><dt className="text-slate-500">RMSE</dt><dd className="font-semibold">{metric(metrics.rmse_mw)} MW</dd></div>
                        <div><dt className="text-slate-500">Bias</dt><dd className="font-semibold">{metric(metrics.mean_bias_error_mw)} MW</dd></div>
                      </dl>
                    </div>
                  )
                })}
              </div>
            </Panel>

            <Panel className="mt-5" title="What-if generation scenarios" subtitle="Illustrative outcomes derived from historical forecast residuals at the first selected cutoff.">
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
                Hypothetical scenario analysis only. These values are not actual forecasts, electricity purchase recommendations, or trading advice.
              </div>
              {errors ? (
                <>
                  <label className="mt-4 grid max-w-xs gap-1 text-sm font-medium text-slate-700">
                    Reference forecast generation (MW)
                    <input
                      type="number"
                      min="0"
                      step="any"
                      value={referenceForecast ?? ''}
                      onChange={(event) => setScenarioForecast(event.target.value === '' ? null : Number(event.target.value))}
                      className="rounded-lg border border-slate-200 px-3 py-2"
                    />
                  </label>
                  <p className="mt-2 text-xs text-slate-500">Based on {data.first_cutoff_matched_observations.toLocaleString('en-GB')} matched historical intervals; residual percentiles are empirical and are not calibrated prediction intervals.</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    {outcomes.map((scenario) => (
                      <div key={scenario.label} className="rounded-lg border border-slate-200 p-4">
                        <p className="text-sm text-slate-500">{scenario.label}</p>
                        <p className="mt-2 text-xl font-semibold">{metric(scenario.mw)} MW</p>
                      </div>
                    ))}
                  </div>
                </>
              ) : <p className="mt-4 text-sm text-slate-500">There are no matched historical errors for the selected first cutoff, so scenario outcomes cannot be calculated.</p>}
            </Panel>
          </>
        ) : null}
      </div>
    </section>
  )
}
