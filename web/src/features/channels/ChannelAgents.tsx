import { useMessages, useChannels } from './hooks'
import { useAgents } from '../agents'
import { useSpawns, type Spawn } from '../spawns'

interface Props {
  channel: string
  onAgentClick?: (agentIdentity: string) => void
}

type SpawnState = 'running' | 'paused' | 'pending' | 'failed' | 'idle'

function getSpawnState(
  spawns: Spawn[],
  agentId: string,
  channelId: string | undefined
): SpawnState {
  const agentSpawns = spawns
    .filter((s) => s.agent_id === agentId && s.channel_id === channelId)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  if (!agentSpawns.length) return 'idle'

  const latest = agentSpawns[0]
  if (latest.status === 'running') return 'running'
  if (latest.status === 'paused') return 'paused'
  if (latest.status === 'pending') return 'pending'
  if (['failed', 'timeout', 'killed'].includes(latest.status)) {
    const endedAt = latest.ended_at ? new Date(latest.ended_at) : null
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000)
    if (endedAt && endedAt > fiveMinAgo) return 'failed'
  }
  return 'idle'
}

function getStatusColor(state: SpawnState): string {
  switch (state) {
    case 'running':
      return 'bg-green-400'
    case 'paused':
      return 'bg-yellow-400'
    case 'pending':
      return 'bg-blue-400 animate-pulse'
    case 'failed':
      return 'bg-red-400'
    default:
      return 'bg-neutral-600'
  }
}

function getStatusLabel(
  state: SpawnState,
  spawns: Spawn[],
  agentId: string,
  channelId: string | undefined
): string | null {
  if (state === 'idle') return null

  const agentSpawns = spawns
    .filter((s) => s.agent_id === agentId && s.channel_id === channelId)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  if (!agentSpawns.length) return null

  const latest = agentSpawns[0]

  if (state === 'running') {
    const started = new Date(latest.created_at)
    const mins = Math.floor((Date.now() - started.getTime()) / 60000)
    return mins < 1 ? 'just started' : `${mins}m`
  }
  if (state === 'paused') return 'paused'
  if (state === 'pending') return 'starting...'
  if (state === 'failed') {
    const ended = latest.ended_at ? new Date(latest.ended_at) : null
    if (ended) {
      const mins = Math.floor((Date.now() - ended.getTime()) / 60000)
      return mins < 1 ? 'failed just now' : `failed ${mins}m ago`
    }
    return 'failed'
  }
  return null
}

export function ChannelAgents({ channel, onAgentClick }: Props) {
  const { data: messages } = useMessages(channel)
  const { data: agents } = useAgents()
  const { data: spawns } = useSpawns()
  const { data: channels } = useChannels()

  const currentChannel = channels?.find((c) => c.name === channel)
  const agentMap = new Map(agents?.map((a) => [a.agent_id, a]) ?? [])

  const channelAgentIds = [...new Set(messages?.map((m) => m.agent_id) ?? [])]

  if (!channelAgentIds.length) {
    return <div className="text-neutral-500 text-sm">No agents yet</div>
  }

  return (
    <div className="space-y-2">
      {channelAgentIds.map((agentId) => {
        const agent = agentMap.get(agentId)
        const state = getSpawnState(spawns ?? [], agentId, currentChannel?.channel_id)
        const label = getStatusLabel(state, spawns ?? [], agentId, currentChannel?.channel_id)
        return (
          <button
            key={agentId}
            onClick={() => agent?.identity && onAgentClick?.(agent.identity)}
            className="flex items-center gap-2 w-full text-left hover:bg-neutral-800 rounded px-2 py-1 -mx-2"
          >
            <span className={`w-2 h-2 rounded-full ${getStatusColor(state)}`} />
            <span className="text-sm text-neutral-300">
              {agent?.identity ?? agentId.slice(0, 7)}
            </span>
            {label && <span className="text-xs text-neutral-500">{label}</span>}
          </button>
        )
      })}
    </div>
  )
}
