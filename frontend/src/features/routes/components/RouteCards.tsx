import type { Route } from '../../../types/plan'
import { RouteCard } from './RouteCard'

export function routeLetter(id: number): string {
  return String.fromCharCode(65 + id)
}

type Props = { routes: Route[]; selectedId: number | null; onSelect: (id: number) => void }

export function RouteCards({ routes, selectedId, onSelect }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          letter={routeLetter(route.id)}
          selected={route.id === selectedId}
          onSelect={() => onSelect(route.id)}
        />
      ))}
    </div>
  )
}
