import { describe, expect, it } from 'vitest'
import { formatLondonDateTime } from './dates'

describe('formatLondonDateTime', () => {
  it('formats timestamps in London daylight-saving time', () => {
    expect(formatLondonDateTime('2026-03-29T01:00:00Z')).toContain('02:00')
  })
})
