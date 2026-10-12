import { Popup } from 'react-map-gl/maplibre'
import { RISK_COLORS, RISK_LABELS } from '../../../theme/risk'
import { formatReading, formatTime } from '../../../utils/format'
import type { CheckpointFeatureProps } from '../utils/to-geojson'

type Props = { checkpoint: CheckpointFeatureProps; onClose: () => void }

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
          Wind {formatReading(checkpoint.wind_mph, 'mph')} (gust {formatReading(checkpoint.gust_mph, 'mph')})
        </div>
        <div>Rain {formatReading(checkpoint.rain_in_hr, 'in/hr', 2)}</div>
        <div>Snow {formatReading(checkpoint.snow_in_hr, 'in/hr', 2)}</div>
      </div>
    </Popup>
  )
}
