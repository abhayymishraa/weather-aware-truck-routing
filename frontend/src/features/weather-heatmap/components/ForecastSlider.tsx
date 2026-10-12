import PauseRounded from '@mui/icons-material/PauseRounded'
import PlayArrowRounded from '@mui/icons-material/PlayArrowRounded'
import IconButton from '@mui/material/IconButton'
import Slider from '@mui/material/Slider'
import Typography from '@mui/material/Typography'
import { useEffect, useState } from 'react'
import { useMap } from 'react-map-gl/maplibre'
import { FORECAST_HOURS } from '../../../config/constants'
import { formatTime } from '../../../utils/format'
import { HEAT_LAYER_ID, heatColor, heatOpacity } from '../utils/heat'

const MARKS = [0, 12, 24, 36, 47].map((value) => ({ value, label: `+${value}h` }))

export function ForecastSlider({ startHour }: { startHour: string }) {
  const { main } = useMap()
  const [hour, setHour] = useState(0)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    const map = main?.getMap()
    if (!map?.getLayer(HEAT_LAYER_ID)) return
    map.setPaintProperty(HEAT_LAYER_ID, 'fill-color', heatColor(hour))
    map.setPaintProperty(HEAT_LAYER_ID, 'fill-opacity', heatOpacity(hour))
  }, [main, hour])

  useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => setHour((h) => (h + 1) % FORECAST_HOURS), 500)
    return () => window.clearInterval(id)
  }, [playing])

  const label = formatTime(new Date(Date.parse(startHour) + hour * 3_600_000).toISOString())

  return (
    <div className="flex items-center gap-3">
      <IconButton
        onClick={() => setPlaying((p) => !p)}
        aria-label={playing ? 'Pause forecast' : 'Play forecast'}
        sx={{ width: 44, height: 44 }}
      >
        {playing ? <PauseRounded /> : <PlayArrowRounded />}
      </IconButton>
      <div className="flex min-w-0 flex-1 flex-col pr-4">
        <Typography variant="caption" aria-live="polite">
          Forecast {label} (+{hour} h)
        </Typography>
        <Slider
          value={hour}
          min={0}
          max={FORECAST_HOURS - 1}
          step={1}
          marks={MARKS}
          onChange={(_, value) => setHour(value as number)}
          aria-label="Forecast hour"
          valueLabelDisplay="off"
        />
      </div>
    </div>
  )
}
