import React, { useEffect, useState } from 'react'
import {
  BashCall,
  BashResult,
  EditCall,
  GenericTool,
  GlobCall,
  GrepCall,
  LSCall,
  MetadataResult,
  ReadCall,
  WriteCall,
} from './ToolRenderers'
import { formatLocalDate } from '../../lib/utils'

interface SessionEvent {
  type: string
  timestamp: string | null
  content: unknown
}

interface Props {
  sessionId?: string | null
  spawnId?: string | null
}

function formatRelativeTime(timestamp: string | null): string {
  if (!timestamp) return ''
  const now = Date.now()
  const then = new Date(timestamp).getTime()
  const diffMs = now - then
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)

  if (diffSec < 60) return `${diffSec}s ago`
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHour < 24) return `${diffHour}h ago`
  return formatLocalDate(timestamp)
}

const MAX_RETRIES = 10
const BASE_DELAY = 2000

export function SessionStream({ sessionId, spawnId }: Props) {
  const [events, setEvents] = useState<SessionEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const endRef = React.useRef<HTMLDivElement>(null)
  const eventSourceRef = React.useRef<globalThis.EventSource | null>(null)
  void retryCount

  const connect = React.useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const streamUrl = sessionId
      ? `/api/sessions/${sessionId}/stream`
      : spawnId
        ? `/api/spawns/${spawnId}/stream`
        : null

    if (!streamUrl) return

    const eventSource = new globalThis.EventSource(streamUrl)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SessionEvent
        setEvents((prev) => [...prev, data])
        setRetryCount(0)
        setError(null)
      } catch {
        // Ignore parse errors
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
      setRetryCount((prev) => {
        const next = prev + 1
        if (next <= MAX_RETRIES) {
          const delay = BASE_DELAY * Math.pow(2, prev)
          globalThis.setTimeout(connect, delay)
          return next
        }
        setError('Failed to load session')
        return next
      })
    }
  }, [sessionId, spawnId])

  useEffect(() => {
    setEvents([])
    setError(null)
    setRetryCount(0)
    connect()

    return () => {
      eventSourceRef.current?.close()
    }
  }, [sessionId, spawnId, connect])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [events])

  const handleManualReconnect = () => {
    setRetryCount(0)
    setError(null)
    connect()
  }

  if (error) {
    return (
      <div className="text-sm">
        <span className="text-red-500">{error}</span>
        <button
          onClick={handleManualReconnect}
          className="ml-2 text-neutral-400 hover:text-white underline"
        >
          Reconnect
        </button>
      </div>
    )
  }

  if (!events.length) {
    return <div className="text-neutral-500 text-sm">Waiting for events...</div>
  }

  const visibleEvents = events.filter((e) => e.type !== 'message')

  const mergedEvents: Array<{
    type: string
    timestamp: string | null
    toolCall?: SessionEvent
    toolResult?: SessionEvent
    textEvent?: SessionEvent
  }> = []

  for (let i = 0; i < visibleEvents.length; i++) {
    const event = visibleEvents[i]
    if (event.type === 'tool_call') {
      const nextEvent = visibleEvents[i + 1]
      const content = event.content as { tool_name: string }
      if (nextEvent?.type === 'tool_result') {
        mergedEvents.push({
          type: content.tool_name,
          timestamp: event.timestamp,
          toolCall: event,
          toolResult: nextEvent,
        })
        i++
      } else {
        mergedEvents.push({
          type: content.tool_name,
          timestamp: event.timestamp,
          toolCall: event,
        })
      }
    } else if (event.type === 'text') {
      mergedEvents.push({
        type: 'text',
        timestamp: event.timestamp,
        textEvent: event,
      })
    } else if (event.type === 'tool_result') {
      mergedEvents.push({
        type: 'tool_result',
        timestamp: event.timestamp,
        toolResult: event,
      })
    }
  }

  return (
    <div className="space-y-3 text-sm overflow-y-auto font-mono">
      {mergedEvents.map((merged, i) => (
        <div key={`${sessionId}-${i}`} className="space-y-1">
          <div className="flex justify-between items-center text-xs text-neutral-600">
            <span>{merged.type}</span>
            <span>{formatRelativeTime(merged.timestamp)}</span>
          </div>
          <div className="space-y-2">
            {merged.toolCall && (
              <div className="font-semibold text-white">
                <EventContent event={merged.toolCall} prevToolCall={undefined} />
              </div>
            )}
            {merged.toolResult && (
              <div className="pl-4 border-l-2 border-neutral-800">
                <EventContent
                  event={merged.toolResult}
                  prevToolCall={
                    merged.toolCall
                      ? (merged.toolCall.content as { tool_name: string }).tool_name
                      : undefined
                  }
                />
              </div>
            )}
            {merged.textEvent && <EventContent event={merged.textEvent} prevToolCall={undefined} />}
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  )
}

const TOOL_RENDERERS: Record<string, (input: Record<string, unknown>) => React.JSX.Element> = {
  Bash: (input) => (
    <BashCall
      command={String(input.command || input.cmd || '')}
      description={input.description ? String(input.description) : undefined}
    />
  ),
  Edit: (input) => (
    <EditCall
      file_path={String(input.file_path || input.path || '')}
      old_string={input.old_string ? String(input.old_string) : undefined}
      new_string={input.new_string ? String(input.new_string) : undefined}
    />
  ),
  MultiEdit: (input) => (
    <EditCall
      file_path={String(input.file_path || '')}
      edits={input.edits as Array<{ old_string: string; new_string: string }> | undefined}
    />
  ),
  Read: (input) => <ReadCall input={input} />,
  Write: (input) => <WriteCall input={input} />,
  Grep: (input) => <GrepCall input={input} />,
  Glob: (input) => <GlobCall input={input} />,
  LS: (input) => <LSCall input={input} />,
}

function EventContent({ event, prevToolCall }: { event: SessionEvent; prevToolCall?: string }) {
  if (event.type === 'text') {
    return <div className="text-neutral-300">{String(event.content)}</div>
  }

  if (event.type === 'tool_call') {
    const content = event.content as { tool_name: string; input: Record<string, unknown> }
    const renderer = TOOL_RENDERERS[content.tool_name]
    return renderer ? (
      renderer(content.input)
    ) : (
      <GenericTool name={content.tool_name} input={content.input} />
    )
  }

  if (event.type === 'tool_result') {
    const content = event.content as { output: string; is_error: boolean }
    const metadataTools = ['Read', 'Grep', 'Glob', 'LS']
    if (prevToolCall && metadataTools.includes(prevToolCall)) {
      return <MetadataResult output={String(content.output)} />
    }
    return <BashResult output={String(content.output)} is_error={content.is_error} />
  }

  return null
}
