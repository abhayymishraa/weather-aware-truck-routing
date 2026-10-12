import Alert from '@mui/material/Alert'
import Paper from '@mui/material/Paper'
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

export function App() {
  const plan = usePlan()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const routes = plan.data?.routes ?? []

  return (
    <MapProvider>
    <div className="flex h-dvh">
      <aside className="w-[400px] overflow-y-auto p-4">
        <div className="flex flex-col gap-4">
          <TripForm
            onSubmit={(request) =>
              plan.mutate(request, {
                onSuccess: (data) => setSelectedId(data.routes[0]?.id ?? null),
              })
            }
            loading={plan.isPending}
          />
          {plan.error && <Alert severity="error">{plan.error.message}</Alert>}
          {plan.data && <WarningBanner warnings={plan.data.warnings} />}
          <RouteCards routes={routes} selectedId={selectedId} onSelect={setSelectedId} />
        </div>
      </aside>
      <main className="relative flex-1">
        <RouteMap routes={routes} selectedId={selectedId} onSelect={setSelectedId}>
          {plan.data && <HeatmapLayer cells={plan.data.heatmap.cells} />}
        </RouteMap>
        {plan.data && (
          <Paper
            className="absolute right-3 bottom-3 flex w-[min(420px,calc(100%-24px))] flex-col gap-1 p-3"
            elevation={3}
          >
            <ForecastSlider
              key={plan.data.heatmap.start_hour + plan.submittedAt}
              startHour={plan.data.heatmap.start_hour}
            />
            <RiskLegend />
          </Paper>
        )}
      </main>
    </div>
    </MapProvider>
  )
}
