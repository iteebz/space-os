import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApi, postApi, deleteApi, postApiNoBody, patchApi } from '../../lib/api'
import type { Channel, Message } from './types'

export function useChannels(archived: boolean = false, readerId?: string) {
  const params = new URLSearchParams()
  params.set('archived', archived.toString())
  if (readerId) {
    params.set('reader_id', readerId)
  }

  return useQuery({
    queryKey: ['channels', archived, readerId],
    queryFn: () => fetchApi<Channel[]>(`/channels?${params.toString()}`),
  })
}

export function useHumanIdentity() {
  return useQuery({
    queryKey: ['identity'],
    queryFn: () => fetchApi<{ identity: string }>('/identity'),
  })
}

export function useMessagesSSE(channel: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const eventSourceRef = useRef<EventSource | null>(null)
  const retryCountRef = useRef(0)
  const maxRetries = 5

  const connect = useCallback(() => {
    if (!channel) return

    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    setIsLoading(true)
    const eventSource = new EventSource(`/api/channels/${channel}/messages/stream`)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as Message
        setMessages((prev) => {
          if (prev.some((m) => m.message_id === msg.message_id)) return prev
          return [...prev, msg]
        })
        setIsLoading(false)
        setError(null)
        retryCountRef.current = 0
      } catch {
        // Ignore parse errors
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
      if (retryCountRef.current < maxRetries) {
        const delay = 1000 * Math.pow(2, retryCountRef.current)
        retryCountRef.current++
        setTimeout(connect, delay)
      } else {
        setError('Connection lost')
        setIsLoading(false)
      }
    }

    eventSource.onopen = () => {
      setIsLoading(false)
      setError(null)
    }
  }, [channel])

  useEffect(() => {
    setMessages([])
    setError(null)
    setIsLoading(true)
    retryCountRef.current = 0
    connect()

    return () => {
      eventSourceRef.current?.close()
    }
  }, [channel, connect])

  return { data: messages, isLoading, error, isError: !!error }
}

export function useMessages(channel: string | null) {
  return useMessagesSSE(channel)
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
