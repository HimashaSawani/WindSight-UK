import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { DecisionPeriodContext } from '../hooks/DecisionPeriodContext'
import type { DecisionPeriod, DecisionPeriodValue } from '../hooks/DecisionPeriodContext'
import { JANUARY_END, JANUARY_START } from '../hooks/DecisionPeriodContext'

export function DecisionPeriodProvider({ children }: { children: ReactNode }) {
  const [range, setRange] = useState<DecisionPeriod>({
    start: JANUARY_START,
    end: JANUARY_END,
  })
  const value = useMemo<DecisionPeriodValue>(() => ({
    ...range,
    setRange,
    setSingleDate: (date) => setRange({ start: date, end: date }),
  }), [range])

  return <DecisionPeriodContext.Provider value={value}>{children}</DecisionPeriodContext.Provider>
}
