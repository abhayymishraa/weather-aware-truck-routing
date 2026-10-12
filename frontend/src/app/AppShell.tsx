import KeyboardArrowUpRounded from '@mui/icons-material/KeyboardArrowUpRounded'
import IconButton from '@mui/material/IconButton'
import LinearProgress from '@mui/material/LinearProgress'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useTheme } from '@mui/material/styles'
import { useState, type ReactNode } from 'react'

const TITLE = 'Weather-aware truck routing'
const OVERLAY_INSET = 150
const SHEET_COLLAPSED = 210

type Props = {
  panel: ReactNode
  map: (bottomInset: number) => ReactNode
  overlay?: ReactNode
  loading?: boolean
  resultKey?: number
}

export function AppShell({ panel, map, overlay, loading, resultKey }: Props) {
  const theme = useTheme()
  const wide = useMediaQuery(theme.breakpoints.up('md'))
  const landscape = useMediaQuery('(orientation: landscape)')
  const [open, setOpen] = useState(true)
  const [seenResult, setSeenResult] = useState(resultKey)
  if (resultKey !== seenResult) {
    setSeenResult(resultKey)
    if (overlay) setOpen(false)
  }
  const progress = loading && <LinearProgress className="absolute inset-x-0 top-0 z-10" />

  if (wide || landscape) {
    return (
      <div className="flex h-dvh w-full">
        <Paper
          square
          elevation={0}
          className="flex h-full w-[320px] shrink-0 flex-col overflow-y-auto lg:w-[400px]"
          sx={{ pl: 'env(safe-area-inset-left)', borderRight: 1, borderColor: 'divider' }}
        >
          <div className="flex flex-col gap-4 p-4">
            <Typography component="h1" variant="h6">
              {TITLE}
            </Typography>
            {panel}
          </div>
        </Paper>
        <main className="relative min-w-0 flex-1">
          {progress}
          {map(overlay ? OVERLAY_INSET : 0)}
          {overlay && (
            <div className="absolute bottom-3 left-3 w-[min(420px,calc(100%-24px))]">{overlay}</div>
          )}
        </main>
      </div>
    )
  }

  return (
    <div className="relative h-dvh w-full overflow-hidden">
      <main className="absolute inset-0">
        {progress}
        {map(SHEET_COLLAPSED)}
      </main>
      <Paper
        elevation={8}
        className="absolute inset-x-0 bottom-0 z-10 flex flex-col rounded-t-2xl transition-[max-height] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:transition-none"
        sx={{ maxHeight: open ? '70dvh' : `${SHEET_COLLAPSED}px`, pb: 'env(safe-area-inset-bottom)' }}
      >
        <div className="flex items-center justify-between px-4 pt-2">
          <Typography component="h1" variant="subtitle1" sx={{ fontWeight: 600 }}>
            {TITLE}
          </Typography>
          <IconButton
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? 'Collapse panel' : 'Expand panel'}
            aria-expanded={open}
            sx={{ width: 44, height: 44 }}
          >
            <KeyboardArrowUpRounded
              className={`transition-[rotate] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:transition-none ${open ? 'rotate-180' : ''}`}
            />
          </IconButton>
        </div>
        <div className="flex flex-col gap-4 overflow-y-auto p-4 pt-1">
          {overlay}
          {panel}
        </div>
      </Paper>
    </div>
  )
}
