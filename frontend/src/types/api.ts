export interface HealthResponse {
  status: 'healthy'
  service: string
}

export interface AccuracyMetrics {
  observation_count: number
  matched_observations: number
  missing_forecasts: number
  missing_actuals: number
  forecast_coverage_pct: number | null
  actual_coverage_pct: number | null
  mean_forecast_mw: number | null
  mean_actual_mw: number | null
  mae_mw: number | null
  rmse_mw: number | null
  mean_bias_error_mw: number | null
  wape_pct: number | null
  maximum_absolute_error_mw: number | null
}

export interface DailyAccuracy {
  decision_date: string
  delivery_date: string
  metrics: AccuracyMetrics
}

export type Availability = 'matched' | 'missing_forecast' | 'missing_actual' | 'missing_both'

export interface ComparisonObservation {
  decision_date: string
  delivery_date: string
  decision_cutoff: string
  target_time: string
  forecast_publish_time: string | null
  forecast_mw: number | null
  actual_mw: number | null
  forecast_age_minutes: number | null
  availability: Availability
  error_mw: number | null
  conflicting_forecast_duplicate: boolean
  conflicting_actual_duplicate: boolean
  forecast_source_metadata: Record<string, unknown> | null
  actual_source_metadata: Record<string, unknown> | null
}

export interface ComparisonResponse {
  decision_cutoff_local_time: string
  timezone: 'Europe/London'
  decision_dates: string[]
  observation_count: number
  observations: ComparisonObservation[]
}

export interface ForecastRevision {
  publish_time: string
  generation_mw: number
  available_at_decision_time: boolean
  selected_for_decision: boolean
  duplicate_publication_timestamp: boolean
  conflicting_duplicate: boolean
}

export interface ForecastRevisionResponse {
  decision_date: string
  delivery_date: string
  target_time: string
  decision_cutoff: string
  decision_cutoff_local_time: string
  timezone: 'Europe/London'
  revisions: ForecastRevision[]
}

export interface AccuracyResponse {
  decision_cutoff_local_time: string
  timezone: 'Europe/London'
  decision_start: string
  decision_end: string
  by_decision_date: DailyAccuracy[]
  by_delivery_date: DailyAccuracy[]
  overall: AccuracyMetrics
}

export interface HistoryResponse {
  decision_cutoff_local_time: string
  timezone: 'Europe/London'
  decision_start: string
  decision_end: string
  days: DailyAccuracy[]
}

export interface OverviewResponse {
  decision_cutoff_local_time: string
  timezone: 'Europe/London'
  decision_start: string
  decision_end: string
  generated_at: string
  metrics: AccuracyMetrics
  daily_history: DailyAccuracy[]
}

export interface BacktestCutoffResult {
  cutoff_local_time: string
  forecast_metrics: AccuracyMetrics
  persistence_metrics: AccuracyMetrics
  persistence_matched_observations: number
}

export interface BacktestResponse {
  decision_start: string
  decision_end: string
  timezone: 'Europe/London'
  first: BacktestCutoffResult
  second: BacktestCutoffResult
  common: {
    matched_observations: number
    first_cutoff_metrics: AccuracyMetrics
    second_cutoff_metrics: AccuracyMetrics
  }
  first_cutoff_error_quantiles_mw: { p10: number; p50: number; p90: number } | null
  first_cutoff_mean_forecast_mw: number | null
  first_cutoff_matched_observations: number
}

export interface APIPerformanceResponse {
  uptime_seconds: number
  requests_in_window: number
  server_errors_in_window: number
  availability_pct: number | null
  mean_response_time_ms: number | null
  p95_response_time_ms: number | null
  total_requests: number
  total_server_errors: number
}

export interface DataQualityResponse {
  status: string
  last_operation: string | null
  last_attempt: string | null
  last_successful_refresh: string | null
  raw_forecast_records: number
  normalized_forecast_records: number
  invalid_forecast_records: number
  raw_actual_records: number
  normalized_actual_records: number
  invalid_actual_records: number
  missing_forecast_records: number
  missing_actual_records: number
  forecast_source_latest_time: string | null
  actual_source_latest_time: string | null
  requests_made: number
  cache_hits: number
  failed_requests: number
  message: string
}
