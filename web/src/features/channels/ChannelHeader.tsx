import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { patchApi } from '../../lib/api'
import type { Channel } from './types'

interface Props {
  channel: Channel
  onInfoClick?: () => void
}

export function ChannelHeader({ channel, onInfoClick }: Props) {
  const [isEditing, setIsEditing] = useState(false)
  const [topic, setTopic] = useState(channel.topic ?? '')
  const queryClient = useQueryClient()

  const { mutate, isPending } = useMutation({
    mutationFn: (newTopic: string) =>
      patchApi(`/channels/${channel.name}/topic`, { topic: newTopic }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
      setIsEditing(false)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (isPending) return
    mutate(topic)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setTopic(channel.topic ?? '')
      setIsEditing(false)
    }
  }

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">#{channel.name}</h2>
        {onInfoClick && (
          <button onClick={onInfoClick} className="text-neutral-500 hover:text-white text-sm">
            info
          </button>
        )}
      </div>
      {isEditing ? (
        <form onSubmit={handleSubmit} className="mt-1">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => {
              setTopic(channel.topic ?? '')
              setIsEditing(false)
            }}
            className="w-full bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-cyan-500"
            placeholder="Set topic..."
            autoFocus
            disabled={isPending}
          />
        </form>
      ) : (
        <p
          onClick={() => setIsEditing(true)}
          className="text-sm text-neutral-400 mt-1 cursor-pointer hover:text-neutral-300"
        >
          {channel.topic || 'Click to set topic...'}
        </p>
      )}
    </div>
  )
}
