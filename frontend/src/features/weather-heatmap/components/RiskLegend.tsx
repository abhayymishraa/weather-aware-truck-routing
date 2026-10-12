import { LEVELS, RISK_COLORS, RISK_LABELS } from '../../../theme/risk'

export function RiskLegend() {
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1 text-xs" aria-label="Risk levels">
      {[...LEVELS, 'no_data' as const].map((level) => (
        <li key={level} className="flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-full" style={{ background: RISK_COLORS[level] }} />
          {RISK_LABELS[level]}
        </li>
      ))}
    </ul>
  )
}
