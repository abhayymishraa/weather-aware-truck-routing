import type { FeatureCollection, Polygon } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import { RISK_COLORS } from '../../../theme/risk'
import type { HeatCell } from '../../../types/plan'

export const HEAT_LAYER_ID = 'corridor-heat'
const HALF_CELL_DEG = 0.125

export function cellsToGeoJSON(cells: HeatCell[]): FeatureCollection<Polygon, Record<string, number>> {
  return {
    type: 'FeatureCollection',
    features: cells.map(({ lat, lon, levels }) => {
      const [west, east, south, north] = [
        lon - HALF_CELL_DEG,
        lon + HALF_CELL_DEG,
        lat - HALF_CELL_DEG,
        lat + HALF_CELL_DEG,
      ]
      return {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
        },
        properties: Object.fromEntries(levels.map((level, hour) => [`h${hour}`, level])),
      }
    }),
  }
}

export function heatColor(hour: number): ExpressionSpecification {
  return [
    'match',
    ['get', `h${hour}`],
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
  ]
}

export function heatOpacity(hour: number): ExpressionSpecification {
  return ['match', ['get', `h${hour}`], 0, 0.1, -1, 0.25, 0.5]
}
