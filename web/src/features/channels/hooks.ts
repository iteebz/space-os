import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApi, postApi } from '../../lib/api'
import type { Channel, Message } from './types'

export function useChannels() {
  return useQuery({
    queryKey: ['channels'],
    queryFn: () => fetchApi<Channel[]>('/channels'),
  })
}

export function useMessages(channel: string | null) {
  return useQuery({
    queryKey: ['messages', channel],
    queryFn: () => fetchApi<Message[]>(`/channels/${channel}/messages`),
    enabled: !!channel,
  })
}

export function useSendMessage(channel: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (content: string) =>
      postApi(`/channels/${channel}/messages`, { content, sender: 'human' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messages', channel] })
    },
  })
}
