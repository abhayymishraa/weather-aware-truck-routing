import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Typography from '@mui/material/Typography'
import { useState, type FormEvent } from 'react'
import {
  DEFAULT_INTERVAL,
  DEFAULT_LOAD_LB,
  FORECAST_HOURS,
  INTERVALS,
  MAX_LOAD_LB,
} from '../../../config/constants'
import type { Interval, Place, PlanRequest } from '../../../types/plan'
import { toLocalInputValue } from '../../../utils/format'
import { PlaceField } from './PlaceField'

const DEPARTURE_GRACE_MS = 15 * 60_000

type Props = { onSubmit: (request: PlanRequest) => void; loading: boolean }

export function TripForm({ onSubmit, loading }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(() => toLocalInputValue(new Date()))
  const [load, setLoad] = useState(String(DEFAULT_LOAD_LB))
  const [interval, setInterval] = useState<Interval>(DEFAULT_INTERVAL)

  const now = new Date()
  const loadValue = Number(load)
  const loadValid = Number.isInteger(loadValue) && loadValue >= 1 && loadValue <= MAX_LOAD_LB
  const canSubmit = origin && destination && departure && loadValid && !loading

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!origin || !destination || !canSubmit) return
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lb: loadValue,
      interval_mi: interval,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <PlaceField label="Origin" value={origin} onChange={setOrigin} />
      <PlaceField label="Destination" value={destination} onChange={setDestination} />
      <TextField
        label="Departure"
        type="datetime-local"
        value={departure}
        onChange={(e) => setDeparture(e.target.value)}
        slotProps={{
          inputLabel: { shrink: true },
          htmlInput: {
            min: toLocalInputValue(new Date(now.getTime() - DEPARTURE_GRACE_MS)),
            max: toLocalInputValue(new Date(now.getTime() + FORECAST_HOURS * 3_600_000)),
          },
        }}
        required
      />
      <TextField
        label="Load weight"
        type="number"
        value={load}
        onChange={(e) => setLoad(e.target.value)}
        error={!loadValid}
        helperText={loadValid ? 'Pounds' : `Enter 1 to ${MAX_LOAD_LB.toLocaleString()} lb`}
        slotProps={{ htmlInput: { min: 1, max: MAX_LOAD_LB, inputMode: 'numeric' } }}
        required
      />
      <div className="flex flex-col gap-1">
        <Typography variant="caption" color="text.secondary">
          Weather checkpoint every
        </Typography>
        <ToggleButtonGroup
          exclusive
          fullWidth
          value={interval}
          onChange={(_, value: Interval | null) => value && setInterval(value)}
        >
          {INTERVALS.map((miles) => (
            <ToggleButton key={miles} value={miles} sx={{ minHeight: 44 }}>
              {miles} mi
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </div>
      <Button type="submit" variant="contained" size="large" disabled={!canSubmit} loading={loading}>
        Find safest route
      </Button>
    </form>
  )
}
