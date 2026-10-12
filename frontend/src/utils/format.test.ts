import { describe, expect, it } from 'vitest'
import { formatDuration, formatMiles, formatReading, toLocalInputValue } from './format'

describe('format', () => {
  it('formats durations', () => {
    expect(formatDuration(45 * 60)).toBe('45 min')
    expect(formatDuration(13 * 3600 + 5 * 60)).toBe('13 h 5 min')
    expect(formatDuration(2 * 3600)).toBe('2 h')
  })

  it('formats miles', () => {
    expect(formatMiles(808.44)).toBe('808 mi')
    expect(formatMiles(4.26)).toBe('4.3 mi')
  })

  it('builds a datetime-local value in local time', () => {
    const date = new Date(2026, 9, 12, 7, 5)
    expect(toLocalInputValue(date)).toBe('2026-10-12T07:05')
  })

  it('formats readings and treats missing values as no data', () => {
    expect(formatReading(18.4, 'mph')).toBe('18 mph')
    expect(formatReading(0.123, 'in/hr', 2)).toBe('0.12 in/hr')
    expect(formatReading(null, 'mph')).toBe('No data')
    expect(formatReading(undefined, 'mph')).toBe('No data')
  })
})
