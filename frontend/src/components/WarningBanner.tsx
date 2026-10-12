import Alert from '@mui/material/Alert'

const MESSAGES: Record<string, { severity: 'error' | 'warning' | 'info'; text: string }> = {
  no_safe_route: { severity: 'error', text: 'No safe route in this window. Every route has No Travel miles.' },
  beyond_forecast: { severity: 'warning', text: 'Part of the trip is past the 48 h forecast. Those miles show as No data.' },
  fallback_routing: { severity: 'info', text: 'Truck routing was not available. These are car routes, so times can be short for a truck.' },
  fewer_routes: { severity: 'info', text: 'Fewer than 3 different routes exist for this trip.' },
}

export function WarningBanner({ warnings }: { warnings: string[] }) {
  return (
    <div className="flex flex-col gap-2">
      {warnings
        .filter((code) => code in MESSAGES)
        .map((code) => (
          <Alert key={code} severity={MESSAGES[code].severity} variant="outlined">
            {MESSAGES[code].text}
          </Alert>
        ))}
    </div>
  )
}
