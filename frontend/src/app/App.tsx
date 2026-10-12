import { TripForm } from '../features/trip-form/components/TripForm'
import { usePlan } from '../features/routes/api/plan'

export function App() {
  const plan = usePlan()
  return (
    <div className="mx-auto max-w-md p-4">
      <TripForm onSubmit={plan.mutate} loading={plan.isPending} />
      <pre className="text-xs">{plan.data ? `${plan.data.routes.length} routes` : plan.error?.message}</pre>
    </div>
  )
}
