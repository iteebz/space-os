import { useChannels } from './hooks'
import type { Channel } from './types'

interface Props {
  selected: string | null
  onSelect: (name: string) => void
}

export function ChannelList({ selected, onSelect }: Props) {
  const { data: channels, isLoading, error } = useChannels()

  if (isLoading) return <div className="text-neutral-500">Loading...</div>
  if (error) return <div className="text-red-500">Error loading channels</div>
  if (!channels?.length) return <div className="text-neutral-500">No channels</div>

  return (
    <ul className="space-y-1">
      {channels.map((channel: Channel) => (
        <li key={channel.name}>
          <button
            onClick={() => onSelect(channel.name)}
            className={`w-full text-left px-2 py-1 rounded text-sm ${
              selected === channel.name
                ? 'bg-neutral-800 text-white'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800/50'
            }`}
          >
            # {channel.name}
            {channel.unread_count > 0 && (
              <span className="ml-2 text-xs text-cyan-400">{channel.unread_count}</span>
            )}
          </button>
        </li>
      ))}
    </ul>
  )
}
