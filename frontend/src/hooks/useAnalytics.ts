import { useQuery } from '@tanstack/react-query'
import { getAccuracy, getComparison, getDataQuality, getForecastRevisions, getHistory, getOverview } from '../services/api'

const queryOptions = { staleTime: 60_000, retry: 2, refetchOnWindowFocus: false }

export function useOverview(start: string, end: string) {
  return useQuery({ ...queryOptions, queryKey: ['overview', start, end], queryFn: () => getOverview({ decision_start: start, decision_end: end }) })
}

export function useComparison(start: string, end: string, decisionDate?: string) {
  return useQuery({
    ...queryOptions,
    queryKey: ['comparison', start, end, decisionDate],
    queryFn: () => getComparison({ decision_start: start, decision_end: end, decision_date: decisionDate }),
  })
}

export function useForecastRevisions(decisionDate: string, targetTime: string) {
  return useQuery({
    ...queryOptions,
    queryKey: ['forecast-revisions', decisionDate, targetTime],
    queryFn: () => getForecastRevisions({ decision_date: decisionDate, target_time: targetTime }),
    enabled: Boolean(decisionDate && targetTime),
  })
}

export function useAccuracy(start: string, end: string, decisionDate?: string) {
  return useQuery({
    ...queryOptions,
    queryKey: ['accuracy', start, end, decisionDate],
    queryFn: () => getAccuracy({ decision_start: start, decision_end: end, decision_date: decisionDate }),
  })
}

export function useHistory(start: string, end: string) {
  return useQuery({ ...queryOptions, queryKey: ['history', start, end], queryFn: () => getHistory({ decision_start: start, decision_end: end }) })
}

export function useDataQuality() {
  return useQuery({ ...queryOptions, queryKey: ['data-quality'], queryFn: getDataQuality, refetchInterval: 30_000 })
}
