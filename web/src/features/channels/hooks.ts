import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApi, postApi, deleteApi, postApiNoBody, patchApi } from '../../lib/api'
import type { Channel, Message } from './types'

export function useChannels(showAll: boolean = false, readerId?: string) {
  const params = new URLSearchParams()
  params.set('show_all', showAll.toString())
  if (readerId) {
    params.set('reader_id', readerId)
  }

  return useQuery({
    queryKey: ['channels', showAll, readerId],
    queryFn: () => fetchApi<Channel[]>(`/channels?${params.toString()}`),
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

export function useSendMessage(channel: string, sender?: string) {
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

export function useRestoreChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (channel: string) => postApiNoBody(`/channels/${channel}/restore`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
  })
}

export function useTogglePinChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (channel: string) => postApiNoBody(`/channels/${channel}/pin`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
  })
}

export function useMarkChannelRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ channel, readerId }: { channel: string; readerId: string }) =>
      postApi(`/channels/${channel}/read`, { reader_id: readerId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
  })
}
