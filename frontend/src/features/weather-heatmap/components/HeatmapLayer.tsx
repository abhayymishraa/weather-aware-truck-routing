import { memo, useMemo } from 'react'
import { Layer, Source } from 'react-map-gl/maplibre'
import type { HeatCell } from '../../../types/plan'
import { cellsToGeoJSON, HEAT_LAYER_ID, heatColor, heatOpacity } from '../utils/heat'

export const HeatmapLayer = memo(function HeatmapLayer({ cells }: { cells: HeatCell[] }) {
  const data = useMemo(() => cellsToGeoJSON(cells), [cells])
  return (
    <Source id="corridor" type="geojson" data={data}>
      <Layer
        id={HEAT_LAYER_ID}
        type="fill"
        paint={{ 'fill-color': heatColor(0), 'fill-opacity': heatOpacity(0) }}
      />
    </Source>
  )
})
