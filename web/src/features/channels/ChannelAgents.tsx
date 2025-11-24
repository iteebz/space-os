import { useMessages, useChannels } from './hooks'
import { useAgents } from '../agents'
import { useSpawns } from '../spawns'

interface Props {
  channel: string
  onAgentClick?: (agentIdentity: string) => void
}

export function ChannelAgents({ channel, onAgentClick }: Props) {
  const { data: messages } = useMessages(channel)
  const { data: agents } = useAgents()
  const { data: spawns } = useSpawns()
  const { data: channels } = useChannels()

  const currentChannel = channels?.find((c) => c.name === channel)
  const agentMap = new Map(agents?.map((a) => [a.agent_id, a]) ?? [])

  // Agent is active if: has messages in last hour OR currently running spawn in this channel
  const now = new Date()
  const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000)

  const recentMessageAgents = new Set(
    messages?.filter((m) => new Date(m.created_at) > oneHourAgo).map((m) => m.agent_id) ?? []
  )

  const runningInChannelAgents = new Set(
    spawns
      ?.filter((s) => s.status === 'running' && s.channel_id === currentChannel?.channel_id)
      .map((s) => s.agent_id) ?? []
  )

  const activeAgents = new Set([...recentMessageAgents, ...runningInChannelAgents])

  const channelAgentIds = [...new Set(messages?.map((m) => m.agent_id) ?? [])]

  if (!channelAgentIds.length) {
    return <div className="text-neutral-500 text-sm">No agents yet</div>
  }

  return (
    <div className="space-y-2">
      {channelAgentIds.map((agentId) => {
        const agent = agentMap.get(agentId)
        const isActive = activeAgents.has(agentId)
        return (
          <button
            key={agentId}
            onClick={() => agent?.identity && onAgentClick?.(agent.identity)}
            className="flex items-center gap-2 w-full text-left hover:bg-neutral-800 rounded px-2 py-1 -mx-2"
          >
            <span
              className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-400' : 'bg-neutral-600'}`}
            />
            <span className="text-sm text-neutral-300">
              {agent?.identity ?? agentId.slice(0, 7)}
            </span>
          </button>
        )
      })}
    </div>
  )
}
