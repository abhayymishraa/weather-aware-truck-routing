import { describe, expect, it } from 'vitest'
import { RISK_COLORS } from '../../../theme/risk'
import { cellsToGeoJSON, heatColor, heatOpacity } from './heat'

describe('heat', () => {
  it('draws each cell as a grid square with hourly levels', () => {
    const levels = Array.from({ length: 48 }, (_, i) => (i === 5 ? 3 : 0))
    const feature = cellsToGeoJSON([{ lat: 30, lon: -97, levels }]).features[0]
    expect(feature.geometry.type).toBe('Polygon')
    expect(feature.geometry.coordinates[0]).toEqual([
      [-97.125, 29.875],
      [-96.875, 29.875],
      [-96.875, 30.125],
      [-97.125, 30.125],
      [-97.125, 29.875],
    ])
    expect(feature.properties.h5).toBe(3)
    expect(feature.properties.h47).toBe(0)
  })

  it('colors an hour by risk level, with gray for no data', () => {
    expect(heatColor(12)).toEqual([
      'match',
      ['get', 'h12'],
      -1,
      RISK_COLORS.no_data,
      0,
      RISK_COLORS.low,
      1,
      RISK_COLORS.moderate,
      2,
      RISK_COLORS.high,
      3,
      RISK_COLORS.severe,
      RISK_COLORS.no_travel,
    ])
  })

  it('keeps low cells faint so risk stands out', () => {
    expect(heatOpacity(3)).toEqual(['match', ['get', 'h3'], 0, 0.1, -1, 0.25, 0.5])
  })
})
