import React, { useState } from 'react'
import { BsPinFill } from 'react-icons/bs'
import {
  useChannels,
  useArchiveChannel,
  useDeleteChannel,
  useRestoreChannel,
  useTogglePinChannel,
  useHumanIdentity,
} from './hooks'
import { QueryState } from '../../lib/QueryState'
import type { Channel } from './types'

interface Props {
  selected: string | null
  onSelect: (name: string) => void
  showArchived: boolean
  isCreating: boolean
  onCreateChannel: (name: string) => void
  onCancelCreate: () => void
}

export function ChannelList({
  selected,
  onSelect,
  showArchived,
  isCreating,
  onCreateChannel,
  onCancelCreate,
}: Props) {
  const { data: identity } = useHumanIdentity()
  const query = useChannels(showArchived, identity?.identity)
  const { mutate: archiveChannel } = useArchiveChannel()
  const { mutate: deleteChannel } = useDeleteChannel()
  const { mutate: restoreChannel } = useRestoreChannel()
  const { mutate: togglePinChannel } = useTogglePinChannel()
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    channel: Channel
  } | null>(null)
  const menuRef = React.useRef<HTMLDivElement>(null)
  const [createName, setCreateName] = useState('')

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

  React.useEffect(() => {
    const handleClick = () => setContextMenu(null)
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [])

  React.useEffect(() => {
    if (contextMenu && menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect()
      const overflow = rect.bottom - window.innerHeight
      if (overflow > 0) {
        menuRef.current.style.top = `${contextMenu.y - rect.height}px`
      }
    }
  }, [contextMenu])

  return (
    <QueryState {...query} empty={<div className="text-neutral-500">No channels</div>}>
      {(channels) => (
        <div className="flex flex-col h-full">
          <ul className="space-y-1 overflow-y-auto scrollable flex-1 min-h-0">
            {isCreating && (
              <li>
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    const name = createName.trim()
                    if (name && !/\s/.test(name)) {
                      onCreateChannel(name)
                      setCreateName('')
                    }
                  }}
                  className="px-2 py-1"
                >
                  <input
                    type="text"
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                    onBlur={() => {
                      setCreateName('')
                      onCancelCreate()
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') {
                        setCreateName('')
                        onCancelCreate()
                      }
                    }}
                    className="w-full bg-neutral-900 border border-neutral-700 rounded px-2 py-0.5 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500"
                    placeholder="channel-name"
                    autoFocus
                  />
                </form>
              </li>
            )}
            {channels.map((channel: Channel) => (
              <li key={channel.name}>
                <button
                  onClick={() => onSelect(channel.name)}
                  onContextMenu={(e) => handleContextMenu(e, channel)}
                  className={`w-full text-left px-2 py-1 rounded text-sm flex items-center gap-1.5 ${
                    selected === channel.name
                      ? 'bg-neutral-800 text-white'
                      : 'text-neutral-400 hover:text-white hover:bg-neutral-800/50'
                  } ${channel.archived_at ? 'opacity-50' : ''}`}
                >
                  {channel.pinned_at && (
                    <BsPinFill className="text-neutral-500 shrink-0" size={12} />
                  )}
                  <span className="flex-1 truncate">{channel.name}</span>
                  {channel.unread_count > 0 && (
                    <span className="w-2 h-2 bg-cyan-500 rounded-full shrink-0" />
                  )}
                </button>
              </li>
            ))}
          </ul>
          {contextMenu && (
            <div
              ref={menuRef}
              className="fixed bg-neutral-800 border border-neutral-700 rounded shadow-lg py-1 z-50"
              style={{ top: contextMenu.y, left: contextMenu.x }}
            >
              {!contextMenu.channel.archived_at && (
                <>
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
