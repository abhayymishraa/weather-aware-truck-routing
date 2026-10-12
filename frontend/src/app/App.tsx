import Alert from '@mui/material/Alert'
import Paper from '@mui/material/Paper'
import Skeleton from '@mui/material/Skeleton'
import { useState } from 'react'
import { MapProvider } from 'react-map-gl/maplibre'
import { WarningBanner } from '../components/WarningBanner'
import { RouteMap } from '../features/map/components/RouteMap'
import { usePlan } from '../features/routes/api/plan'
import { RouteCards } from '../features/routes/components/RouteCards'
import { TripForm } from '../features/trip-form/components/TripForm'
import { ForecastSlider } from '../features/weather-heatmap/components/ForecastSlider'
import { HeatmapLayer } from '../features/weather-heatmap/components/HeatmapLayer'
import { RiskLegend } from '../features/weather-heatmap/components/RiskLegend'
import { AppShell } from './AppShell'

export function App() {
  const plan = usePlan()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const routes = plan.data?.routes ?? []

  const panel = (
    <>
      <TripForm
        onSubmit={(request) =>
          plan.mutate(request, { onSuccess: (data) => setSelectedId(data.routes[0]?.id ?? null) })
        }
        loading={plan.isPending}
      />
      {plan.error && <Alert severity="error">{plan.error.message}</Alert>}
      {plan.data && <WarningBanner warnings={plan.data.warnings} />}
      {plan.isPending ? (
        <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading routes">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} variant="rounded" height={132} />
          ))}
        </div>
      ) : (
        <RouteCards routes={routes} selectedId={selectedId} onSelect={setSelectedId} />
      )}
    </>
  )

  const overlay = plan.data && (
    <Paper elevation={3} className="flex flex-col gap-1 p-3">
      <ForecastSlider
        key={`${plan.data.heatmap.start_hour}-${plan.submittedAt}`}
        startHour={plan.data.heatmap.start_hour}
      />
      <RiskLegend />
    </Paper>
  )

  return (
    <MapProvider>
      <AppShell
        panel={panel}
        overlay={overlay}
        loading={plan.isPending}
        resultKey={plan.data ? plan.submittedAt : undefined}
        map={(bottomInset) => (
          <RouteMap
            routes={routes}
            selectedId={selectedId}
            onSelect={setSelectedId}
            bottomInset={bottomInset}
          >
            {plan.data && <HeatmapLayer cells={plan.data.heatmap.cells} />}
          </RouteMap>
        )}
      />
    </MapProvider>
  )
}
