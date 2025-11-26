import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../../lib/api'
import type { Agent, Memory } from './types'

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => fetchApi<Agent[]>('/agents'),
  })
}

export function useAgent(identity: string | null) {
  const { data: agents } = useAgents()
  return agents?.find((a) => a.identity === identity) ?? null
}

export function useAgentMemories(identity: string | null) {
  return useQuery({
    queryKey: ['memories', identity],
    queryFn: () => fetchApi<Memory[]>(`/agents/${identity}/memories`),
    enabled: !!identity,
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
