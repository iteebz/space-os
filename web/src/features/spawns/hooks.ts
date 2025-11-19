import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../../lib/api'
import type { Spawn } from './types'

export function useSpawns() {
  return useQuery({
    queryKey: ['spawns'],
    queryFn: () => fetchApi<Spawn[]>('/spawns'),
  })
}
