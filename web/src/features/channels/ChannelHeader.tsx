import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { patchApi } from '../../lib/api'
import type { Channel } from './types'

interface Props {
  channel: Channel
  onInfoClick?: () => void
  onExportClick?: () => void
}

export function ChannelHeader({ channel, onInfoClick, onExportClick }: Props) {
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
        <div className="flex items-center gap-2">
          {onExportClick && (
            <button
              onClick={onExportClick}
              className="text-neutral-500 hover:text-white text-sm"
              title="Copy channel messages"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z" />
                <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z" />
              </svg>
            </button>
          )}
          {onInfoClick && (
            <button onClick={onInfoClick} className="text-neutral-500 hover:text-white text-sm">
              info
            </button>
          )}
        </div>
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
