import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'

const OverviewPage = lazy(() => import('./pages/OverviewPage').then(({ OverviewPage }) => ({ default: OverviewPage })))
const BacktestingPage = lazy(() => import('./pages/BacktestingPage').then(({ BacktestingPage }) => ({ default: BacktestingPage })))
const ForecastExplorerPage = lazy(() => import('./pages/SectionPage').then(({ ForecastExplorerPage }) => ({ default: ForecastExplorerPage })))
const AccuracyAnalysisPage = lazy(() => import('./pages/SectionPage').then(({ AccuracyAnalysisPage }) => ({ default: AccuracyAnalysisPage })))
const HistoricalAnalysisPage = lazy(() => import('./pages/SectionPage').then(({ HistoricalAnalysisPage }) => ({ default: HistoricalAnalysisPage })))
const MethodologyPage = lazy(() => import('./pages/SectionPage').then(({ MethodologyPage }) => ({ default: MethodologyPage })))

function App() {
  return (
    <Suspense fallback={<main className="grid min-h-screen place-items-center p-6 text-sm text-slate-600" role="status">Loading WindSight UK...</main>}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/forecasts" element={<ForecastExplorerPage />} />
          <Route path="/accuracy" element={<AccuracyAnalysisPage />} />
          <Route path="/history" element={<HistoricalAnalysisPage />} />
          <Route path="/backtesting" element={<BacktestingPage />} />
          <Route path="/methodology" element={<MethodologyPage />} />
          <Route path="*" element={<OverviewPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default App
