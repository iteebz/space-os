import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApi, postApi, deleteApi, postApiNoBody } from '../../lib/api'
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

export function useArchiveChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (channel: string) => postApiNoBody(`/channels/${channel}/archive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
  })
}

export function useDeleteChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (channel: string) => deleteApi(`/channels/${channel}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
  })
}

export function useDeleteMessage(channel: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (messageId: string) => deleteApi(`/messages/${messageId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messages', channel] })
    },
  })
}
