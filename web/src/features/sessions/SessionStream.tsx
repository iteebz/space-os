import React, { useEffect, useState } from 'react'
import { BashCall, BashResult, EditCall, GenericTool } from './ToolRenderers'

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
  return new Date(timestamp).toLocaleDateString()
}

export function SessionStream({ sessionId }: Props) {
  const [events, setEvents] = useState<SessionEvent[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const eventSource = new window.EventSource(`/api/sessions/${sessionId}/stream`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SessionEvent
        setEvents((prev) => [...prev, data])
      } catch {
        // Ignore parse errors
      }
    }

    eventSource.onerror = () => {
      setError('Connection lost')
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [sessionId])

  if (error) {
    return <div className="text-red-500 text-sm">{error}</div>
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
