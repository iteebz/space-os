import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApi, postApi, deleteApi, postApiNoBody, patchApi } from '../../lib/api'
import type { Channel, Message } from './types'

export function useChannels() {
  return useQuery({
    queryKey: ['channels'],
    queryFn: () => fetchApi<Channel[]>('/channels'),
  })
}

export function useHumanIdentity() {
  return useQuery({
    queryKey: ['identity'],
    queryFn: () => fetchApi<{ identity: string }>('/identity'),
  })
}

export function useMessages(channel: string | null) {
  return useQuery({
    queryKey: ['messages', channel],
    queryFn: () => fetchApi<Message[]>(`/channels/${channel}/messages`),
    enabled: !!channel,
  })
}

export function useSendMessage(channel: string, sender: string = 'human') {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (content: string) => postApi(`/channels/${channel}/messages`, { content, sender }),
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

export function useRenameChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ channel, newName }: { channel: string; newName: string }) =>
      patchApi(`/channels/${channel}`, { new_name: newName }),
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
