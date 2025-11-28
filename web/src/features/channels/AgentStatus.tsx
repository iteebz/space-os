import { useSpawns } from '../spawns'
import { useAgentMap } from '../agents'
import { useChannels } from './hooks'
import { useQuery } from '@tanstack/react-query'

interface Props {
  channel: string
}

interface AgentActivity {
  agent_id: string
  identity: string
  description: string
  timestamp: string
}

export function AgentStatus({ channel }: Props) {
  const { data: spawns } = useSpawns()
  const { data: channels } = useChannels()
  const agentMap = useAgentMap()

  const currentChannel = channels?.find((c) => c.name === channel)

  const activeSpawns = spawns?.filter(
    (s) => s.status === 'running' && s.channel_id === currentChannel?.channel_id
  )

  const { data: activities = [] } = useQuery<AgentActivity[]>({
    queryKey: ['agent-activities', activeSpawns?.map((s) => s.session_id).join(',')],
    queryFn: async () => {
      if (!activeSpawns?.length) return []

      const results = await Promise.all(
        activeSpawns.map(async (spawn) => {
          if (!spawn.session_id) return null
          try {
            const res = await fetch(`/api/sessions/${spawn.session_id}/last-tool`)
            if (!res.ok) return null
            const data = await res.json()
            return {
              agent_id: spawn.agent_id,
              identity: agentMap.get(spawn.agent_id) ?? spawn.agent_id.slice(0, 8),
              description: data.description ?? '',
              timestamp: data.timestamp ?? '',
            }
          } catch {
            return null
          }
        })
      )

      return results.filter((r): r is AgentActivity => r !== null && r.description !== '')
    },
    enabled: !!activeSpawns?.length,
    refetchInterval: 2000,
  })

  if (!activities.length) return null

  return (
    <div className="mb-3 pb-3 border-b border-neutral-800">
      {activities.map((activity) => (
        <div key={activity.agent_id} className="flex items-baseline gap-2 text-xs text-neutral-500">
          <span className="text-cyan-400">{activity.identity}</span>
          <span>·</span>
          <span>{activity.description}</span>
          <span>·</span>
          <span>{formatRelativeTime(activity.timestamp)}</span>
        </div>
      ))}
    </div>
  )
}

function formatRelativeTime(timestamp: string): string {
  if (!timestamp) return ''
  const now = Date.now()
  const then = new Date(timestamp).getTime()
  const diffSec = Math.floor((now - then) / 1000)
  const diffMin = Math.floor(diffSec / 60)

  if (diffSec < 60) return `${diffSec}s ago`
  if (diffMin < 60) return `${diffMin}m ago`
  return `${Math.floor(diffMin / 60)}h ago`
}
