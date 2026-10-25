import { describe, expect, it } from 'vitest'
import { getDecisionDates } from './decisionDates'

describe('getDecisionDates', () => {
  it('includes both bounds and crosses month boundaries', () => {
    expect(getDecisionDates('2026-01-30', '2026-02-02')).toEqual([
      '2026-01-30',
      '2026-01-31',
      '2026-02-01',
      '2026-02-02',
    ])
  })

  it('returns one date when the bounds are equal', () => {
    expect(getDecisionDates('2026-01-31', '2026-01-31')).toEqual(['2026-01-31'])
  })
})
