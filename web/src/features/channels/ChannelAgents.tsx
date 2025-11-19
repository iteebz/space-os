import { useMessages } from './hooks'
import { useAgents } from '../agents'
import { useSpawns } from '../spawns'

interface Props {
  channel: string
}

export function ChannelAgents({ channel }: Props) {
  const { data: messages } = useMessages(channel)
  const { data: agents } = useAgents()
  const { data: spawns } = useSpawns()

  const agentMap = new Map(agents?.map((a) => [a.agent_id, a]) ?? [])
  const runningAgents = new Set(
    spawns?.filter((s) => s.status === 'running').map((s) => s.agent_id) ?? []
  )

  const channelAgentIds = [...new Set(messages?.map((m) => m.agent_id) ?? [])]

  if (!channelAgentIds.length) {
    return <div className="text-neutral-500 text-sm">No agents yet</div>
  }

  return (
    <div className="space-y-2">
      {channelAgentIds.map((agentId) => {
        const agent = agentMap.get(agentId)
        const isRunning = runningAgents.has(agentId)
        return (
          <div key={agentId} className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-400' : 'bg-neutral-600'}`}
            />
            <span className="text-sm text-neutral-300">
              {agent?.identity ?? agentId.slice(0, 7)}
            </span>
            {agent?.role && <span className="text-xs text-neutral-500 truncate">{agent.role}</span>}
          </div>
        )
      })}
    </div>
  )
}
