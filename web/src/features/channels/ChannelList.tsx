import React, { useState } from 'react'
import { useChannels, useArchiveChannel, useDeleteChannel } from './hooks'
import { QueryState } from '../../lib/QueryState'
import type { Channel } from './types'

interface Props {
  selected: string | null
  onSelect: (name: string) => void
}

export function ChannelList({ selected, onSelect }: Props) {
  const query = useChannels()
  const { mutate: archiveChannel } = useArchiveChannel()
  const { mutate: deleteChannel } = useDeleteChannel()
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; channel: string } | null>(
    null
  )

  const handleContextMenu = (e: React.MouseEvent, channelName: string) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, channel: channelName })
  }

  const handleArchive = () => {
    if (contextMenu) {
      archiveChannel(contextMenu.channel)
      setContextMenu(null)
    }
  }

  const handleDelete = () => {
    if (contextMenu) {
      deleteChannel(contextMenu.channel)
      setContextMenu(null)
    }
  }

  React.useEffect(() => {
    const handleClick = () => setContextMenu(null)
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [])

  return (
    <QueryState {...query} empty={<div className="text-neutral-500">No channels</div>}>
      {(channels) => (
        <>
          <ul className="space-y-1">
            {channels.map((channel: Channel) => (
              <li key={channel.name}>
                <button
                  onClick={() => onSelect(channel.name)}
                  onContextMenu={(e) => handleContextMenu(e, channel.name)}
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
          {contextMenu && (
            <div
              className="fixed bg-neutral-800 border border-neutral-700 rounded shadow-lg py-1 z-50"
              style={{ top: contextMenu.y, left: contextMenu.x }}
            >
              <button
                onClick={handleArchive}
                className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-700 hover:text-white"
              >
                Archive
              </button>
              <button
                onClick={handleDelete}
                className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-neutral-700 hover:text-red-300"
              >
                Delete
              </button>
            </div>
          )}
        </>
      )}
    </QueryState>
  )
}
