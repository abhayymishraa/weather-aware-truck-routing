import { useMutation } from '@tanstack/react-query'
import { api, type ApiError } from '../../../lib/api'
import type { Plan, PlanRequest } from '../../../types/plan'

export function usePlan() {
  return useMutation<Plan, ApiError, PlanRequest>({
    mutationFn: (request) => api<Plan>('/plan', { method: 'POST', body: JSON.stringify(request) }),
  })
}
