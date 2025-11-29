import React, { useState, useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
import { useMessages, useDeleteMessage } from './hooks'
import { useAgentMap, useAgentIdentities } from '../agents'
import { useSpawns } from '../spawns'
import { QueryState } from '../../lib/QueryState'
import { formatLocalTime } from '../../lib/utils'
import { formatDateDivider, isSameDay } from '../../lib/time'
import type { Message } from './types'

interface Props {
  channelName: string
  channelId: string | undefined
}

interface ElementWithProps {
  props?: { children?: unknown }
}

function extractText(node: unknown): string {
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractText).join('')
  if (typeof node === 'object' && node !== null && 'props' in node) {
    return extractText((node as ElementWithProps).props?.children)
  }
  return ''
}

function getIdentityColor(identity: string): string {
  const hash = identity.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0)
  const colors = [
    'text-cyan-400',
    'text-emerald-400',
    'text-purple-400',
    'text-orange-400',
    'text-pink-400',
    'text-yellow-400',
    'text-blue-400',
    'text-rose-400',
  ]
  return colors[hash % colors.length]
}

function getMentionColor(identity: string): { bg: string; text: string } {
  const hash = identity.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0)
  const colors = [
    { bg: 'bg-cyan-900', text: 'text-cyan-200' },
    { bg: 'bg-emerald-900', text: 'text-emerald-200' },
    { bg: 'bg-purple-900', text: 'text-purple-200' },
    { bg: 'bg-orange-900', text: 'text-orange-200' },
    { bg: 'bg-pink-900', text: 'text-pink-200' },
    { bg: 'bg-yellow-900', text: 'text-yellow-200' },
    { bg: 'bg-blue-900', text: 'text-blue-200' },
    { bg: 'bg-rose-900', text: 'text-rose-200' },
  ]
  return colors[hash % colors.length]
}

function highlightDelimiters(content: unknown, validIdentities: Set<string>): React.ReactNode {
  const text = extractText(content)
  const parts = text.split(/(@[\w-]+|~\/[\w/.@-]+|\.\/[\w/.@-]*)/g)
  return parts.map((part, idx) => {
    if (!part) return null
    if (part.startsWith('@')) {
      const identity = part.slice(1)
      if (!validIdentities.has(identity)) return part
      const colors = getMentionColor(identity)
      return (
        <span
          key={idx}
          className={`px-1.5 py-0.5 ${colors.bg} ${colors.text} rounded-lg font-medium`}
        >
          {part}
        </span>
      )
    }
    if (part.startsWith('~/') || part.startsWith('./')) {
      return (
        <span
          key={idx}
          className="px-1.5 py-0.5 bg-neutral-800 text-neutral-300 rounded font-mono text-xs"
        >
          {part}
        </span>
      )
    }
    return part
  })
}

function DelimiterHighlighter({
  content,
  validIdentities,
}: {
  content: unknown
  validIdentities: Set<string>
}) {
  return <>{highlightDelimiters(content, validIdentities)}</>
}

export function MessageList({ channelName, channelId }: Props) {
  const query = useMessages(channelName)
  const agentMap = useAgentMap()
  const agentIdentities = useAgentIdentities()
  const { data: spawns } = useSpawns()
  const deleteMessage = useDeleteMessage(channelName)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const activeAgentIds = new Set(
    spawns
      ?.filter(
        (s) =>
          s.status === 'running' &&
          s.channel_id === channelId &&
          s.agent_id !== '019aadf4-acb1-7623-8f08-cac86d68d39a'
      )
      .map((s) => s.agent_id) ?? []
  )

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [query.data])

  return (
    <QueryState {...query} empty={<div className="text-neutral-500">No messages</div>}>
      {(messages) => (
        <div className="space-y-4">
          {messages.map((msg: Message, idx: number) => {
            const showDateDivider =
              idx === 0 || !isSameDay(messages[idx - 1].created_at, msg.created_at)
            return (
              <React.Fragment key={msg.message_id}>
                {showDateDivider && (
                  <div className="flex items-center gap-3 my-6">
                    <div className="h-px bg-neutral-800 flex-1" />
                    <span className="text-xs text-neutral-500 font-medium">
                      {formatDateDivider(msg.created_at)}
                    </span>
                    <div className="h-px bg-neutral-800 flex-1" />
                  </div>
                )}
                <div
                  className="border-b border-neutral-800 pb-4 relative group"
                  onMouseEnter={() => setHoveredId(msg.message_id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`font-semibold ${getIdentityColor(
                          agentMap.get(msg.agent_id) ?? msg.agent_id
                        )}`}
                      >
                        {agentMap.get(msg.agent_id) ?? msg.agent_id.slice(0, 7)}
                      </span>
                      {msg.agent_id !== '019aadf4-acb1-7623-8f08-cac86d68d39a' && (
                        <span
                          className={`w-2 h-2 rounded-full ${
                            activeAgentIds.has(msg.agent_id) ? 'bg-green-400' : 'bg-neutral-600'
                          }`}
                        />
                      )}
                    </div>
                    <span className="text-xs text-neutral-500">
                      {formatLocalTime(msg.created_at)}
                    </span>
                    {hoveredId === msg.message_id && (
                      <div className="ml-auto flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => navigator.clipboard.writeText(msg.content)}
                          className="text-neutral-400 hover:text-neutral-200 p-1"
                          title="Copy message"
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z" />
                            <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => deleteMessage.mutate(msg.message_id)}
                          className="text-red-400 hover:text-red-300 p-1"
                          title="Delete message"
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z" />
                            <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="text-neutral-300 text-sm prose prose-invert prose-sm max-w-none prose-strong:text-white prose-headings:text-white prose-p:my-2 prose-li:my-1 break-words overflow-wrap-anywhere">
                    <Markdown
                      components={{
                        p: ({ children }) => (
                          <p>
                            <DelimiterHighlighter
                              content={children}
                              validIdentities={agentIdentities}
                            />
                          </p>
                        ),
                        strong: ({ children }) => (
                          <strong>
                            <DelimiterHighlighter
                              content={children}
                              validIdentities={agentIdentities}
                            />
                          </strong>
                        ),
                        em: ({ children }) => (
                          <em>
                            <DelimiterHighlighter
                              content={children}
                              validIdentities={agentIdentities}
                            />
                          </em>
                        ),
                      }}
                    >
                      {msg.content}
                    </Markdown>
                  </div>
                </div>
              </React.Fragment>
            )
          })}
          <div ref={messagesEndRef} />
        </div>
      )}
    </QueryState>
  )
}
