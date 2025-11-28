import React, { useState } from 'react'
import { BsPinFill } from 'react-icons/bs'
import {
  useChannels,
  useArchiveChannel,
  useDeleteChannel,
  useRenameChannel,
  useRestoreChannel,
  useTogglePinChannel,
  useHumanIdentity,
} from './hooks'
import { QueryState } from '../../lib/QueryState'
import type { Channel } from './types'

interface Props {
  selected: string | null
  onSelect: (name: string) => void
}

export function ChannelList({ selected, onSelect }: Props) {
  const [showArchived, setShowArchived] = useState(false)
  const { data: identity } = useHumanIdentity()
  const query = useChannels(showArchived, identity?.identity)
  const { mutate: archiveChannel } = useArchiveChannel()
  const { mutate: deleteChannel } = useDeleteChannel()
  const { mutate: renameChannel } = useRenameChannel()
  const { mutate: restoreChannel } = useRestoreChannel()
  const { mutate: togglePinChannel } = useTogglePinChannel()
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    channel: Channel
  } | null>(null)
  const [renaming, setRenaming] = useState<string | null>(null)
  const [newName, setNewName] = useState('')

  const handleContextMenu = (e: React.MouseEvent, channel: Channel) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, channel })
  }

  const handleArchive = () => {
    if (contextMenu) {
      archiveChannel(contextMenu.channel.name)
      setContextMenu(null)
    }
  }

  const handleRestore = () => {
    if (contextMenu) {
      restoreChannel(contextMenu.channel.name)
      setContextMenu(null)
    }
  }

  const handleTogglePin = () => {
    if (contextMenu) {
      togglePinChannel(contextMenu.channel.name)
      setContextMenu(null)
    }
  }

  const handleDelete = () => {
    if (contextMenu) {
      deleteChannel(contextMenu.channel.name)
      setContextMenu(null)
    }
  }

  const handleRenameClick = () => {
    if (contextMenu) {
      setNewName(contextMenu.channel.name)
      setRenaming(contextMenu.channel.name)
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
        <div className="flex flex-col h-full">
          <div className="mb-3">
            <label className="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer hover:text-neutral-300">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
                className="w-4 h-4 rounded border border-neutral-600 bg-neutral-900 checked:bg-cyan-600 checked:border-cyan-600 focus:ring-2 focus:ring-cyan-500 focus:ring-offset-0 cursor-pointer"
              />
              Show archived
            </label>
          </div>
          <ul className="space-y-1 overflow-y-auto scrollable flex-1 min-h-0">
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
                    onContextMenu={(e) => handleContextMenu(e, channel)}
                    className={`w-full text-left px-2 py-1 rounded text-sm flex items-center gap-1 ${
                      selected === channel.name
                        ? 'bg-neutral-800 text-white'
                        : 'text-neutral-400 hover:text-white hover:bg-neutral-800/50'
                    } ${channel.archived_at ? 'opacity-50' : ''}`}
                  >
                    {channel.pinned_at && (
                      <BsPinFill className="text-neutral-500 shrink-0" size={12} />
                    )}
                    <span className="flex-1 truncate"># {channel.name}</span>
                    {channel.unread_count > 0 && (
                      <span className="w-2 h-2 bg-cyan-500 rounded-full shrink-0" />
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
              {!contextMenu.channel.archived_at && (
                <>
                  <button
                    onClick={handleRenameClick}
                    className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-700 hover:text-white"
                  >
                    Rename
                  </button>
                  <button
                    onClick={handleTogglePin}
                    className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-700 hover:text-white"
                  >
                    {contextMenu.channel.pinned_at ? 'Unpin' : 'Pin'}
                  </button>
                  <button
                    onClick={handleArchive}
                    className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-700 hover:text-white"
                  >
                    Archive
                  </button>
                </>
              )}
              {contextMenu.channel.archived_at && (
                <button
                  onClick={handleRestore}
                  className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-700 hover:text-white"
                >
                  Restore
                </button>
              )}
              <button
                onClick={handleDelete}
                className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-neutral-700 hover:text-red-300"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      )}
    </QueryState>
  )
}
