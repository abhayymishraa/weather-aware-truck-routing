import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TripForm } from './TripForm'

const client = new QueryClient()

function form(loading = false) {
  return (
    <QueryClientProvider client={client}>
      <TripForm onSubmit={() => {}} loading={loading} />
    </QueryClientProvider>
  )
}

describe('TripForm', () => {
  afterEach(() => vi.useRealTimers())

  it('default load passes native validation', () => {
    render(form())
    expect(screen.getByLabelText(/Load weight/)).toBeValid()
  })

  it('default departure stays valid a few minutes later', () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    const { rerender } = render(form())
    vi.setSystemTime(Date.now() + 5 * 60_000)
    rerender(form(true))
    expect(screen.getByLabelText(/Departure/)).toBeValid()
  })
})
