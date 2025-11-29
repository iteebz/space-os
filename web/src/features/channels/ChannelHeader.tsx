import React, { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { patchApi } from '../../lib/api'
import type { Channel } from './types'
import { useRenameChannel } from './hooks'
import { formatTimeRemaining } from '../../lib/time'

interface Props {
  channel: Channel
  onInfoClick?: () => void
  onExportClick?: () => Promise<boolean | void>
  isCreating?: boolean
  onCreate?: (name: string, topic: string | null) => void
  onCancelCreate?: () => void
  createError?: unknown
}

export function ChannelHeader({
  channel,
  onInfoClick,
  onExportClick,
  isCreating = false,
  onCreate,
  onCancelCreate,
  createError,
}: Props) {
  const [isEditingTopic, setIsEditingTopic] = useState(isCreating)
  const [isEditingName, setIsEditingName] = useState(isCreating)
  const [topic, setTopic] = useState(channel.topic ?? '')
  const [name, setName] = useState(channel.name)
  const [showCopied, setShowCopied] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [timerDisplay, setTimerDisplay] = useState('')
  const queryClient = useQueryClient()
  const { mutate: renameChannel } = useRenameChannel()

  const { mutate: updateTopic, isPending: isTopicPending } = useMutation({
    mutationFn: (newTopic: string) =>
      patchApi(`/channels/${channel.name}/topic`, { topic: newTopic }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
      setIsEditingTopic(false)
    },
  })

  const handleTopicSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (isTopicPending) return
    updateTopic(topic)
  }

  const handleTopicKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (isCreating) {
        onCancelCreate?.()
      } else {
        setTopic(channel.topic ?? '')
        setIsEditingTopic(false)
      }
    }
  }

  const handleNameSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setValidationError(null)

    if (!name.trim()) {
      setValidationError('Channel name required')
      return
    }

    if (isCreating) {
      onCreate?.(name.trim(), topic.trim() || null)
    } else if (name !== channel.name) {
      renameChannel({ channel: channel.name, newName: name })
      setIsEditingName(false)
    } else {
      setIsEditingName(false)
    }
  }

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (isCreating) {
        onCancelCreate?.()
      } else {
        setName(channel.name)
        setIsEditingName(false)
      }
    } else if (e.key === 'Tab' && isCreating) {
      e.preventDefault()
      const syntheticEvent = { preventDefault: () => {} } as React.FormEvent
      handleNameSubmit(syntheticEvent)
      setIsEditingTopic(true)
    }
  }

  const handleExportClick = async () => {
    const success = await onExportClick?.()
    if (success !== false) setShowCopied(true)
  }

  useEffect(() => {
    if (showCopied) {
      const timer = window.setTimeout(() => setShowCopied(false), 2000)
      return () => window.clearTimeout(timer)
    }
  }, [showCopied])

  useEffect(() => {
    if (createError) {
      const error = createError as Error & { message?: string }
      const errorMsg = error?.message || 'Failed to create channel'
      if (errorMsg.includes('exists') || errorMsg.includes('already')) {
        setValidationError('Channel already exists')
      } else {
        setValidationError(errorMsg)
      }
    }
  }, [createError])

  useEffect(() => {
    if (!isEditingName) {
      setName(channel.name)
    }
    if (!isEditingTopic) {
      setTopic(channel.topic ?? '')
    }
  }, [channel.name, channel.topic, isEditingName, isEditingTopic])

  useEffect(() => {
    if (!channel.timer_expires_at) {
      setTimerDisplay('')
      return
    }

    const updateTimer = () => {
      setTimerDisplay(formatTimeRemaining(channel.timer_expires_at))
    }

    updateTimer()
    const interval = window.setInterval(updateTimer, 30000)
    return () => window.clearInterval(interval)
  }, [channel.timer_expires_at])

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between">
        <div className="flex flex-col">
          <div className="flex items-center gap-1">
            <span className="text-lg font-semibold text-white">#</span>
            {isEditingName || isCreating ? (
              <form onSubmit={handleNameSubmit}>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value)
                    setValidationError(null)
                  }}
                  onKeyDown={handleNameKeyDown}
                  onBlur={() => {
                    if (isCreating) {
                      if (name.trim()) {
                        handleNameSubmit({ preventDefault: () => {} } as React.FormEvent)
                      }
                    } else {
                      setName(channel.name)
                      setIsEditingName(false)
                    }
                  }}
                  className="bg-transparent border-none px-1 text-lg font-semibold text-white focus:outline-none focus:ring-0"
                  style={{ outline: 'none' }}
                  placeholder={isCreating ? 'channel-name' : ''}
                  autoFocus
                />
              </form>
            ) : (
              <h2
                onClick={() => setIsEditingName(true)}
                className="text-lg font-semibold text-white cursor-text hover:text-neutral-300 px-1"
              >
                {channel.name}
              </h2>
            )}
          </div>
          {validationError && <p className="text-sm text-red-400 mt-1">{validationError}</p>}
        </div>
        <div className="flex items-center gap-2">
          {timerDisplay && (
            <div className="text-sm text-amber-400" title="Auto-stop timer">
              ⏱️ {timerDisplay}
            </div>
          )}
          {onExportClick && (
            <button
              onClick={handleExportClick}
              className="text-neutral-500 hover:text-white text-sm"
              title={showCopied ? 'Copied!' : 'Copy channel messages'}
            >
              {showCopied ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z" />
                  <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z" />
                </svg>
              )}
            </button>
          )}
          {onInfoClick && (
            <button onClick={onInfoClick} className="text-neutral-500 hover:text-white text-sm">
              info
            </button>
          )}
        </div>
      </div>
      {isEditingTopic ? (
        <form onSubmit={handleTopicSubmit} className="mt-1">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={handleTopicKeyDown}
            onBlur={() => {
              setTopic(channel.topic ?? '')
              setIsEditingTopic(false)
            }}
            className="w-full bg-transparent border-none m-0 px-0 py-0 text-sm text-neutral-400 placeholder-neutral-500 focus:outline-none focus:ring-0 leading-normal h-5"
            style={{ outline: 'none' }}
            placeholder="Add topic..."
            autoFocus
            disabled={isTopicPending}
          />
        </form>
      ) : (
        <p
          onClick={() => setIsEditingTopic(true)}
          className={`text-sm mt-1 m-0 cursor-text hover:text-neutral-300 leading-normal h-5 ${
            channel.topic ? 'text-neutral-400' : 'text-neutral-600'
          }`}
        >
          {channel.topic || 'Add topic'}
        </p>
      )}
    </div>
  )
}
