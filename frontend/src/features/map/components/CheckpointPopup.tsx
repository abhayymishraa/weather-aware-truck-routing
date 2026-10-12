import { Popup } from 'react-map-gl/maplibre'
import { RISK_COLORS, RISK_LABELS } from '../../../theme/risk'
import { formatTime } from '../../../utils/format'
import type { CheckpointFeatureProps } from '../utils/to-geojson'

type Props = { checkpoint: CheckpointFeatureProps; onClose: () => void }

function value(n: number | null, unit: string, digits = 0) {
  return n === null ? 'No data' : `${n.toFixed(digits)} ${unit}`
}

export function CheckpointPopup({ checkpoint, onClose }: Props) {
  return (
    <Popup
      longitude={checkpoint.lon}
      latitude={checkpoint.lat}
      onClose={onClose}
      closeOnClick={false}
      maxWidth="260px"
    >
      <div className="flex flex-col gap-1 text-sm text-neutral-900">
        <div className="flex items-center gap-2 font-semibold">
          <span
            className="inline-block size-3 rounded-full"
            style={{ background: RISK_COLORS[checkpoint.level] }}
          />
          {RISK_LABELS[checkpoint.level]} · mile {Math.round(checkpoint.mile)}
        </div>
        <div>ETA {formatTime(checkpoint.eta)}</div>
        <div>
          Wind {value(checkpoint.wind_mph, 'mph')} (gust {value(checkpoint.gust_mph, 'mph')})
        </div>
        <div>Rain {value(checkpoint.rain_in_hr, 'in/hr', 2)}</div>
        <div>Snow {value(checkpoint.snow_in_hr, 'in/hr', 2)}</div>
      </div>
    </Popup>
  )
}
