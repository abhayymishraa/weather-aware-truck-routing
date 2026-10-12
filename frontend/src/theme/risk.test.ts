import { describe, expect, it } from 'vitest'
import { riskKey, RISK_COLORS, RISK_LABELS } from './risk'

describe('risk scale', () => {
  it('maps null to no_data', () => {
    expect(riskKey(null)).toBe('no_data')
    expect(riskKey('severe')).toBe('severe')
  })

  it('has a color and a label for every key', () => {
    for (const key of ['low', 'moderate', 'high', 'severe', 'no_travel', 'no_data'] as const) {
      expect(RISK_COLORS[key]).toMatch(/^#[0-9a-f]{6}$/i)
      expect(RISK_LABELS[key]).toBeTruthy()
    }
  })
})
