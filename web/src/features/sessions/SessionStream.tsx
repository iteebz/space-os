import React, { useEffect, useState } from 'react'
import { BashCall, BashResult, EditCall, GenericTool } from './ToolRenderers'
import { formatLocalDate } from '../../lib/utils'

interface SessionEvent {
  type: string
  timestamp: string | null
  content: unknown
}

interface Props {
  sessionId: string
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

const MAX_RETRIES = 3
const BASE_DELAY = 1000

export function SessionStream({ sessionId }: Props) {
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

    const eventSource = new globalThis.EventSource(`/api/sessions/${sessionId}/stream`)
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
        setError('Connection lost')
        return next
      })
    }
  }, [sessionId])

  useEffect(() => {
    setEvents([])
    setError(null)
    setRetryCount(0)
    connect()

    return () => {
      eventSourceRef.current?.close()
    }
  }, [sessionId, connect])

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

  return (
    <div className="space-y-3 text-sm overflow-y-auto font-mono">
      {events.map((event, i) => (
        <div key={`${sessionId}-${i}`} className="space-y-1">
          <div className="flex justify-between items-center text-xs text-neutral-600">
            <span>{event.type}</span>
            <span>{formatRelativeTime(event.timestamp)}</span>
          </div>
          <div className={event.type === 'tool_result' ? 'pl-4 border-l-2 border-neutral-800' : ''}>
            <EventContent event={event} />
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
      command={String(input.command || '')}
      description={input.description ? String(input.description) : undefined}
    />
  ),
  Edit: (input) => (
    <EditCall
      file_path={String(input.file_path || '')}
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
}

function EventContent({ event }: { event: SessionEvent }) {
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
    return <BashResult output={String(content.output)} is_error={content.is_error} />
  }

  return <pre className="text-xs text-neutral-500">{JSON.stringify(event.content, null, 2)}</pre>
}
