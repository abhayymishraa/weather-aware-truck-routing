import { LEVELS, RISK_COLORS, RISK_LABELS } from '../../../theme/risk'
import type { Route } from '../../../types/plan'
import { formatMiles } from '../../../utils/format'

const KEYS = [...LEVELS, 'no_data'] as const

export function RiskBar({ miles }: { miles: Route['miles_by_level'] }) {
  const total = KEYS.reduce((sum, key) => sum + miles[key], 0) || 1
  const shown = KEYS.filter((key) => miles[key] > 0)
  return (
    <div className="flex flex-col gap-1.5">
      <div
        className="flex h-2 w-full gap-0.5 overflow-hidden rounded-full"
        role="img"
        aria-label="Miles by risk level"
      >
        {shown.map((key) => (
          <div
            key={key}
            style={{ flexGrow: miles[key] / total, background: RISK_COLORS[key] }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
        {shown.map((key) => (
          <span key={key} className="inline-flex items-center gap-1">
            <span className="size-2 rounded-sm" style={{ background: RISK_COLORS[key] }} />
            {formatMiles(miles[key])} {RISK_LABELS[key]}
          </span>
        ))}
      </div>
    </div>
  )
}
