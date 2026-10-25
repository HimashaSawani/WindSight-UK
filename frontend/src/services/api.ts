import axios, { isAxiosError } from 'axios'
import type {
  AccuracyResponse,
  ComparisonResponse,
  DataQualityResponse,
  ForecastRevisionResponse,
  HealthResponse,
  HistoryResponse,
  OverviewResponse,
} from '../types/api'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120_000,
})

export function getApiErrorMessage(error: unknown): string {
  if (isAxiosError<{ detail?: { message?: string } | string }>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (detail?.message) return detail.message
    if (!error.response) return 'The API could not be reached. Check that the backend is running and retry.'
    return `The API returned HTTP ${error.response.status}. Retry or check the backend data-quality endpoint.`
  }
  return error instanceof Error ? error.message : 'An unexpected error occurred.'
}

interface DateRange {
  decision_start: string
  decision_end: string
}

export async function getHealth(): Promise<HealthResponse> {
  return (await api.get<HealthResponse>('/health')).data
}

export async function getOverview(params: DateRange): Promise<OverviewResponse> {
  return (await api.get<OverviewResponse>('/overview', { params })).data
}

export async function getComparison(params: DateRange & { decision_date?: string }): Promise<ComparisonResponse> {
  return (await api.get<ComparisonResponse>('/comparison', { params })).data
}

export async function getForecastRevisions(params: { decision_date: string; target_time: string }): Promise<ForecastRevisionResponse> {
  return (await api.get<ForecastRevisionResponse>('/forecast-revisions', { params })).data
}

export async function getAccuracy(params: DateRange & { decision_date?: string }): Promise<AccuracyResponse> {
  return (await api.get<AccuracyResponse>('/accuracy', { params })).data
}

export async function getHistory(params: DateRange): Promise<HistoryResponse> {
  return (await api.get<HistoryResponse>('/history', { params })).data
}

export async function getDataQuality(): Promise<DataQualityResponse> {
  return (await api.get<DataQualityResponse>('/data-quality')).data
}
