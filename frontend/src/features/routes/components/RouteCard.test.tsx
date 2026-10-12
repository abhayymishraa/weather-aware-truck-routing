import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Route } from '../../../types/plan'
import { RouteCard } from './RouteCard'

const route: Route = {
  id: 0,
  geometry: { type: 'LineString', coordinates: [] },
  distance_mi: 808.4,
  duration_s: 13 * 3600 + 5 * 60,
  source: 'tomtom',
  checkpoints: [],
  miles_by_level: { low: 700, moderate: 58.4, high: 50, severe: 0, no_travel: 0, no_data: 0 },
  avg_risk: 0.2,
  rank: 1,
  recommended: true,
  reason: 'Fewest High miles',
}

describe('RouteCard', () => {
  it('shows the summary and the recommendation', () => {
    render(<RouteCard route={route} letter="A" selected={false} onSelect={() => {}} />)
    expect(screen.getByText('Recommended')).toBeInTheDocument()
    expect(screen.getByText('808 mi')).toBeInTheDocument()
    expect(screen.getByText('13 h 5 min')).toBeInTheDocument()
    expect(screen.getByText('Fewest High miles')).toBeInTheDocument()
    expect(screen.getByText(/50 mi High/)).toBeInTheDocument()
  })

  it('selects on click', async () => {
    const onSelect = vi.fn()
    render(<RouteCard route={route} letter="A" selected={false} onSelect={onSelect} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onSelect).toHaveBeenCalledOnce()
  })
})
