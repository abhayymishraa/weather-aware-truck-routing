import { describe, expect, it } from 'vitest'
import type { Route } from '../../../types/plan'
import { checkpointsToGeoJSON, routesToGeoJSON } from './to-geojson'

const route: Route = {
  id: 2,
  geometry: { type: 'LineString', coordinates: [[-97, 32], [-105, 39]] },
  distance_mi: 800,
  duration_s: 3600,
  source: 'tomtom',
  checkpoints: [
    {
      mile: 0,
      lat: 32,
      lon: -97,
      eta: '2026-10-12T05:00:00+00:00',
      wind_mph: 5,
      gust_mph: 9,
      rain_in_hr: 0,
      snow_in_hr: 0,
      level: null,
      segment_mi: 12.5,
    },
  ],
  miles_by_level: { low: 0, moderate: 0, high: 0, severe: 0, no_travel: 0, no_data: 800 },
  avg_risk: null,
  rank: 1,
  recommended: true,
  reason: 'Only route found',
}

describe('to-geojson', () => {
  it('keeps route id and recommendation on each line', () => {
    const data = routesToGeoJSON([route])
    expect(data.features[0].properties).toEqual({ id: 2, recommended: true })
    expect(data.features[0].geometry).toBe(route.geometry)
  })

  it('places checkpoints at lon, lat with the route id and a risk key', () => {
    const feature = checkpointsToGeoJSON([route]).features[0]
    expect(feature.geometry.coordinates).toEqual([-97, 32])
    expect(feature.properties.routeId).toBe(2)
    expect(feature.properties.level).toBe('no_data')
  })
})
