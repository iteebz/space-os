import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../../lib/api'
import type { Agent } from './types'

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => fetchApi<Agent[]>('/agents'),
  })
}
