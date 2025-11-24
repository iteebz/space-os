import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../../lib/api'
import type { Agent } from './types'

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => fetchApi<Agent[]>('/agents'),
  })
}

export function useAgentMap() {
  const { data: agents } = useAgents()
  return new Map(agents?.map((a) => [a.agent_id, a.identity]) ?? [])
}

export function useAgentIdentities() {
  const { data: agents } = useAgents()
  return new Set(agents?.map((a) => a.identity) ?? [])
}
