import { memo, useMemo } from 'react'
import { Layer, Source } from 'react-map-gl/maplibre'
import { RISK_COLORS } from '../../../theme/risk'
import type { HeatCell } from '../../../types/plan'
import { cellsToGeoJSON, HEAT_LAYER_ID, heatWeight } from '../utils/heat'

export const HeatmapLayer = memo(function HeatmapLayer({ cells }: { cells: HeatCell[] }) {
  const data = useMemo(() => cellsToGeoJSON(cells), [cells])
  return (
    <Source id="corridor" type="geojson" data={data}>
      <Layer
        id={HEAT_LAYER_ID}
        type="heatmap"
        paint={{
          'heatmap-weight': heatWeight(0),
          'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 3, 0.6, 8, 1.2],
          'heatmap-radius': ['interpolate', ['exponential', 2], ['zoom'], 3, 10, 6, 40, 9, 160],
          'heatmap-opacity': 0.7,
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0,
            'rgba(0,0,0,0)',
            0.15,
            RISK_COLORS.moderate,
            0.4,
            RISK_COLORS.high,
            0.65,
            RISK_COLORS.severe,
            0.9,
            RISK_COLORS.no_travel,
          ],
        }}
      />
    </Source>
  )
})
