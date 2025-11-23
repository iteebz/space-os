import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../../lib/api'

interface Session {
  session_id: string
  provider: string
  model: string
  first_message_at: string | null
  last_message_at: string | null
}

interface Props {
  agentId: string
  channelId?: string
  onSessionClick: (sessionId: string) => void
}

export function SessionList({ agentId, channelId, onSessionClick }: Props) {
  const {
    data: sessions,
    error,
    isLoading,
  } = useQuery({
    queryKey: channelId
      ? ['channel-agent-sessions', channelId, agentId]
      : ['agent-sessions', agentId],
    queryFn: () =>
      channelId
        ? fetchApi<Session[]>(`/channels/${channelId}/agents/${agentId}/sessions`)
        : fetchApi<Session[]>(`/agents/${agentId}/sessions`),
    retry: false,
  })

  if (isLoading) {
    return <div className="text-neutral-500 text-sm">Loading sessions...</div>
  }

  if (error) {
    return <div className="text-red-500 text-sm">No sessions found</div>
  }

  if (!sessions?.length) {
    return <div className="text-neutral-500 text-sm">No sessions</div>
  }

  return (
    <div className="space-y-2">
      {sessions.map((session) => (
        <button
          key={session.session_id}
          onClick={() => onSessionClick(session.session_id)}
          className="w-full text-left p-2 rounded hover:bg-neutral-800 border border-neutral-800"
        >
          <div className="text-sm text-neutral-300 truncate">{session.session_id.slice(0, 8)}</div>
          <div className="text-xs text-neutral-500">
            {session.provider} · {session.model}
          </div>
          {session.last_message_at && (
            <div className="text-xs text-neutral-600">
              {new Date(session.last_message_at).toLocaleDateString()}
            </div>
          )}
        </button>
      ))}
    </div>
  )
}
