import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { OverviewPage } from './pages/OverviewPage'
import { BacktestingPage } from './pages/BacktestingPage'
import {
  AccuracyAnalysisPage,
  ForecastExplorerPage,
  HistoricalAnalysisPage,
  MethodologyPage,
} from './pages/SectionPage'

function App() {
  return (
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
  )
}

export default App
