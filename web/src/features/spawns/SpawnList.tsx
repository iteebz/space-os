import { useSpawns } from './hooks'
import { useAgents } from '../agents'
import type { Spawn } from './types'

interface Props {
  selected: string | null
  onSelect: (id: string) => void
  channelId?: string | null
}

function statusColor(status: string): string {
  switch (status) {
    case 'running':
      return 'text-green-400'
    case 'paused':
      return 'text-yellow-400'
    case 'completed':
      return 'text-neutral-500'
    case 'failed':
      return 'text-red-400'
    default:
      return 'text-neutral-400'
  }
}

function statusBadge(status: string): string {
  switch (status) {
    case 'running':
      return 'R'
    case 'paused':
      return 'P'
    case 'pending':
      return 'W'
    case 'completed':
      return '✓'
    case 'failed':
      return '✗'
    default:
      return '?'
  }
}

export function SpawnList({ selected, onSelect, channelId }: Props) {
  const { data: spawns, isLoading, error } = useSpawns()
  const { data: agents } = useAgents()

  const agentMap = new Map(agents?.map((a) => [a.agent_id, a.identity]) ?? [])

  if (isLoading) return <div className="text-neutral-500">Loading...</div>
  if (error) return <div className="text-red-500">Error loading spawns</div>

  const filtered = channelId
    ? spawns?.filter((s) => s.channel_id === channelId)
    : spawns

  if (!filtered?.length) {
    return (
      <div className="text-neutral-500">
        {channelId ? 'No spawns in this channel' : 'No spawns'}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <ul className="space-y-1 flex-1 overflow-y-auto">
        {filtered.map((spawn: Spawn) => (
          <li key={spawn.id}>
            <button
              onClick={() => onSelect(spawn.id)}
              className={`w-full text-left px-2 py-1 rounded text-sm font-mono ${
                selected === spawn.id
                  ? 'bg-neutral-800 text-white'
                  : 'text-neutral-400 hover:text-white hover:bg-neutral-800/50'
              }`}
            >
              <span className={statusColor(spawn.status)}>{statusBadge(spawn.status)}</span>{' '}
              <span className="text-cyan-400">{agentMap.get(spawn.agent_id) ?? '?'}</span>{' '}
              {spawn.id.slice(0, 7)}
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-4 pt-2 border-t border-neutral-800 text-xs text-neutral-500">
        <span className="text-green-400">R</span> running{' '}
        <span className="text-yellow-400">P</span> paused{' '}
        <span className="text-neutral-400">W</span> pending{' '}
        <span className="text-neutral-500">✓</span> done{' '}
        <span className="text-red-400">✗</span> failed
      </div>
    </div>
  )
}
