import { createContext } from 'react'

export interface DecisionPeriod {
  start: string
  end: string
}

export interface DecisionPeriodValue extends DecisionPeriod {
  setRange: (range: DecisionPeriod) => void
  setSingleDate: (date: string) => void
}

export const DecisionPeriodContext = createContext<DecisionPeriodValue | null>(null)
export const JANUARY_START = '2026-01-01'
export const JANUARY_END = '2026-01-31'
