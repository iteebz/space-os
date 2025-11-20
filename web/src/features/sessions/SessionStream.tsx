import { useEffect, useState } from 'react'

interface SessionEvent {
  type: string
  timestamp: string | null
  content: unknown
}

interface Props {
  sessionId: string
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
    <div className="space-y-2 text-sm overflow-y-auto">
      {events.map((event, i) => (
        <div key={i} className="border-b border-neutral-800 pb-2">
          <div className="text-xs text-neutral-500 mb-1">
            {event.type}
            {event.timestamp && (
              <span className="ml-2">{new Date(event.timestamp).toLocaleTimeString()}</span>
            )}
          </div>
          <div className="text-neutral-300">
            <EventContent event={event} />
          </div>
        </div>
      ))}
    </div>
  )
}

function EventContent({ event }: { event: SessionEvent }) {
  if (event.type === 'text') {
    return <span>{String(event.content)}</span>
  }

  if (event.type === 'tool_call') {
    const content = event.content as { tool_name: string; input: unknown }
    return (
      <div>
        <span className="text-cyan-400">{content.tool_name}</span>
        <pre className="text-xs text-neutral-500 mt-1 overflow-x-auto">
          {JSON.stringify(content.input, null, 2)}
        </pre>
      </div>
    )
  }

  if (event.type === 'tool_result') {
    const content = event.content as { output: string; is_error: boolean }
    return (
      <pre
        className={`text-xs overflow-x-auto ${content.is_error ? 'text-red-400' : 'text-neutral-400'}`}
      >
        {String(content.output).slice(0, 500)}
        {String(content.output).length > 500 && '...'}
      </pre>
    )
  }

  return <pre className="text-xs">{JSON.stringify(event.content, null, 2)}</pre>
}
