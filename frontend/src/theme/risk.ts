import type { LevelName, RiskKey } from '../types/plan'

export const LEVELS: readonly LevelName[] = ['low', 'moderate', 'high', 'severe', 'no_travel']

export const RISK_COLORS: Record<RiskKey, string> = {
  low: '#0ca30c',
  moderate: '#fab219',
  high: '#e8692a',
  severe: '#bb2230',
  no_travel: '#8b3fc6',
  no_data: '#9aa5ad',
}

export const RISK_LABELS: Record<RiskKey, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No Travel',
  no_data: 'No data',
}

export function riskKey(level: LevelName | null): RiskKey {
  return level ?? 'no_data'
}
