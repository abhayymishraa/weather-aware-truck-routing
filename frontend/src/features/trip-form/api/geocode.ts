import { useQuery } from '@tanstack/react-query'
import { api } from '../../../lib/api'
import type { Place } from '../../../types/plan'

export function useGeocode(query: string) {
  const q = query.trim()
  return useQuery({
    queryKey: ['geocode', q.toLowerCase()],
    queryFn: ({ signal }) =>
      api<{ results: Place[] }>(`/geocode?q=${encodeURIComponent(q)}`, { signal }).then(
        (body) => body.results,
      ),
    enabled: q.length >= 3,
    staleTime: Infinity,
    placeholderData: (previous) => previous,
  })
}
