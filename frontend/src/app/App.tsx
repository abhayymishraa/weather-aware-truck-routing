import Alert from '@mui/material/Alert'
import { useState } from 'react'
import { WarningBanner } from '../components/WarningBanner'
import { RouteMap } from '../features/map/components/RouteMap'
import { usePlan } from '../features/routes/api/plan'
import { RouteCards } from '../features/routes/components/RouteCards'
import { TripForm } from '../features/trip-form/components/TripForm'

export function App() {
  const plan = usePlan()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const routes = plan.data?.routes ?? []

  return (
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
        <RouteMap routes={routes} selectedId={selectedId} onSelect={setSelectedId} />
      </main>
    </div>
  )
}
