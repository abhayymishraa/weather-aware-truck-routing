import type { FeatureCollection, LineString, Point } from 'geojson'
import { riskKey } from '../../../theme/risk'
import type { Checkpoint, RiskKey, Route } from '../../../types/plan'

export type CheckpointFeatureProps = Omit<Checkpoint, 'level'> & { routeId: number; level: RiskKey }

export function routesToGeoJSON(
  routes: Route[],
): FeatureCollection<LineString, { id: number; recommended: boolean }> {
  return {
    type: 'FeatureCollection',
    features: routes.map((route) => ({
      type: 'Feature',
      geometry: route.geometry,
      properties: { id: route.id, recommended: route.recommended },
    })),
  }
}

export function checkpointsToGeoJSON(
  routes: Route[],
): FeatureCollection<Point, CheckpointFeatureProps> {
  return {
    type: 'FeatureCollection',
    features: routes.flatMap((route) =>
      route.checkpoints.map((checkpoint) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [checkpoint.lon, checkpoint.lat] },
        properties: { ...checkpoint, routeId: route.id, level: riskKey(checkpoint.level) },
      })),
    ),
  }
}
