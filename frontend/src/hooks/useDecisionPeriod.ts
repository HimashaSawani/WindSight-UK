import { useContext } from 'react'
import { DecisionPeriodContext } from './DecisionPeriodContext'

export function useDecisionPeriod() {
  const value = useContext(DecisionPeriodContext)
  if (!value) throw new Error('useDecisionPeriod must be used inside DecisionPeriodProvider.')
  return value
}
