import Card from '@mui/material/Card'
import CardActionArea from '@mui/material/CardActionArea'
import Chip from '@mui/material/Chip'
import Typography from '@mui/material/Typography'
import type { Route } from '../../../types/plan'
import { formatDuration, formatMiles } from '../../../utils/format'
import { RiskBar } from './RiskBar'

type Props = { route: Route; letter: string; selected: boolean; onSelect: () => void }

export function RouteCard({ route, letter, selected, onSelect }: Props) {
  return (
    <Card
      variant="outlined"
      sx={{ borderColor: selected ? 'primary.main' : undefined, borderWidth: selected ? 2 : 1 }}
    >
      <CardActionArea onClick={onSelect} aria-pressed={selected} sx={{ p: 2 }}>
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2">
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Route {letter}
            </Typography>
            {route.recommended && <Chip label="Recommended" color="primary" size="small" />}
          </div>
          <div className="flex gap-4 text-sm">
            <span>{formatMiles(route.distance_mi)}</span>
            <span>{formatDuration(route.duration_s)}</span>
            <span>
              Avg risk {route.avg_risk === null ? 'No data' : route.avg_risk.toFixed(2)}
            </span>
          </div>
          <RiskBar miles={route.miles_by_level} />
          <Typography variant="body2" color="text.secondary">
            {route.reason}
          </Typography>
        </div>
      </CardActionArea>
    </Card>
  )
}
