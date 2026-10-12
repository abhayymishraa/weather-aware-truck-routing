import type { LineString } from 'geojson'

export type LevelName = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'
export type RiskKey = LevelName | 'no_data'
export type Interval = 10 | 25 | 50

export type Place = { label: string; lat: number; lon: number }

export type Checkpoint = {
  mile: number
  lat: number
  lon: number
  eta: string
  wind_mph: number | null
  gust_mph: number | null
  rain_in_hr: number | null
  snow_in_hr: number | null
  level: LevelName | null
  segment_mi: number
}

export type Route = {
  id: number
  geometry: LineString
  distance_mi: number
  duration_s: number
  source: 'tomtom' | 'osrm'
  checkpoints: Checkpoint[]
  miles_by_level: Record<RiskKey, number>
  avg_risk: number | null
  rank: number
  recommended: boolean
  reason: string
}

export type HeatCell = { lat: number; lon: number; levels: number[] }

export type Plan = {
  routes: Route[]
  heatmap: { start_hour: string; cells: HeatCell[] }
  warnings: string[]
}

export type PlanRequest = {
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_mi: Interval
}
