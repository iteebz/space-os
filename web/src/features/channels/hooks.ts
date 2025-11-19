import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../../lib/api'
import type { Channel } from './types'

export function useChannels() {
  return useQuery({
    queryKey: ['channels'],
    queryFn: () => fetchApi<Channel[]>('/channels'),
  })
}

export function useMessages(channel: string | null) {
  return useQuery({
    queryKey: ['messages', channel],
    queryFn: () => fetchApi<{ messages: unknown[] }>(`/channels/${channel}/messages`),
    enabled: !!channel,
  })
}
