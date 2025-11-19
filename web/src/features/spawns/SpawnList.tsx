import { useSpawns } from './hooks'
import type { Spawn } from './types'

interface Props {
  selected: string | null
  onSelect: (id: string) => void
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

export function SpawnList({ selected, onSelect }: Props) {
  const { data: spawns, isLoading, error } = useSpawns()

  if (isLoading) return <div className="text-neutral-500">Loading...</div>
  if (error) return <div className="text-red-500">Error loading spawns</div>
  if (!spawns?.length) return <div className="text-neutral-500">No active spawns</div>

  return (
    <ul className="space-y-1">
      {spawns.map((spawn: Spawn) => (
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
            {spawn.id.slice(0, 7)}
          </button>
        </li>
      ))}
    </ul>
  )
}
