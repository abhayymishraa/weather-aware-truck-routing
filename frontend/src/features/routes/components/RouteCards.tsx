import type { Route } from '../../../types/plan'
import { RouteCard } from './RouteCard'

function routeLetter(id: number): string {
  return String.fromCharCode(65 + id)
}

type Props = { routes: Route[]; selectedId: number | null; onSelect: (id: number) => void }

export function RouteCards({ routes, selectedId, onSelect }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {routes.map((route, i) => (
        <div
          key={route.id}
          className="transition-[opacity,translate] ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:starting:translate-y-0 duration-200 starting:translate-y-1 starting:opacity-0"
          style={{ transitionDelay: `${i * 50}ms` }}
        >
          <RouteCard
            route={route}
            letter={routeLetter(route.id)}
            selected={route.id === selectedId}
            onSelect={() => onSelect(route.id)}
          />
        </div>
      ))}
    </div>
  )
}
