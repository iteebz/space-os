import React, { useState } from 'react'
import { useChannels, useArchiveChannel, useDeleteChannel, useRenameChannel } from './hooks'
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
  const { mutate: renameChannel } = useRenameChannel()
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; channel: string } | null>(
    null
  )
  const [renaming, setRenaming] = useState<string | null>(null)
  const [newName, setNewName] = useState('')

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

  const handleRenameClick = () => {
    if (contextMenu) {
      setNewName(contextMenu.channel)
      setRenaming(contextMenu.channel)
      setContextMenu(null)
    }
  }

  const handleRenameSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (renaming && newName && newName !== renaming) {
      renameChannel({ channel: renaming, newName })
    }
    setRenaming(null)
    setNewName('')
  }

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setRenaming(null)
      setNewName('')
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
                {renaming === channel.name ? (
                  <form onSubmit={handleRenameSubmit} className="px-2 py-1">
                    <input
                      type="text"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      onKeyDown={handleRenameKeyDown}
                      onBlur={() => {
                        setRenaming(null)
                        setNewName('')
                      }}
                      className="w-full bg-neutral-900 border border-neutral-700 rounded px-2 py-0.5 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500"
                      autoFocus
                    />
                  </form>
                ) : (
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
                )}
              </li>
            ))}
          </ul>
          {contextMenu && (
            <div
              className="fixed bg-neutral-800 border border-neutral-700 rounded shadow-lg py-1 z-50"
              style={{ top: contextMenu.y, left: contextMenu.x }}
            >
              <button
                onClick={handleRenameClick}
                className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-700 hover:text-white"
              >
                Rename
              </button>
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
