import { describe, expect, it } from 'vitest'
import { cellsToGeoJSON, heatWeight } from './heat'

describe('heat', () => {
  it('flattens hourly levels into properties', () => {
    const levels = Array.from({ length: 48 }, (_, i) => (i === 5 ? 3 : 0))
    const data = cellsToGeoJSON([{ lat: 30, lon: -97, levels }])
    const feature = data.features[0]
    expect(feature.geometry.coordinates).toEqual([-97, 30])
    expect(feature.properties.h5).toBe(3)
    expect(feature.properties.h47).toBe(0)
  })

  it('builds the weight expression for an hour', () => {
    expect(heatWeight(12)).toEqual(['/', ['max', ['get', 'h12'], 0], 4])
  })
})
