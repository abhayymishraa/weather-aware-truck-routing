import type { FeatureCollection, Point } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import type { HeatCell } from '../../../types/plan'

export const HEAT_LAYER_ID = 'corridor-heat'

export function cellsToGeoJSON(cells: HeatCell[]): FeatureCollection<Point, Record<string, number>> {
  return {
    type: 'FeatureCollection',
    features: cells.map((cell) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [cell.lon, cell.lat] },
      properties: Object.fromEntries(cell.levels.map((level, hour) => [`h${hour}`, level])),
    })),
  }
}

export function heatWeight(hour: number): ExpressionSpecification {
  return ['/', ['max', ['get', `h${hour}`], 0], 4]
}
