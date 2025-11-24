import { useSpawns } from './hooks'
import { useAgentMap } from '../agents'
import { QueryState } from '../../lib/QueryState'
import type { Spawn } from './types'

interface Props {
  selected: string | null
  onSelect: (id: string) => void
  channelId?: string | null
}

const STATUS_COLORS: Record<string, string> = {
  running: 'text-green-400',
  paused: 'text-yellow-400',
  completed: 'text-neutral-500',
  failed: 'text-red-400',
}

const STATUS_BADGES: Record<string, string> = {
  running: 'R',
  paused: 'P',
  pending: 'W',
  completed: '✓',
  failed: '✗',
}

export function SpawnList({ selected, onSelect, channelId }: Props) {
  const query = useSpawns()
  const agentMap = useAgentMap()

  return (
    <QueryState
      {...query}
      empty={
        <div className="text-neutral-500">
          {channelId ? 'No spawns in this channel' : 'No spawns'}
        </div>
      }
    >
      {(spawns) => {
        const filtered = channelId ? spawns.filter((s) => s.channel_id === channelId) : spawns
        if (!filtered.length) {
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
                    <span className={STATUS_COLORS[spawn.status] ?? 'text-neutral-400'}>
                      {STATUS_BADGES[spawn.status] ?? '?'}
                    </span>{' '}
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
      }}
    </QueryState>
  )
}
