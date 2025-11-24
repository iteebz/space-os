import React, { useState, useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
import { useMessages, useDeleteMessage } from './hooks'
import { useAgentMap } from '../agents'
import { QueryState } from '../../lib/QueryState'
import type { Message } from './types'

interface Props {
  channel: string
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

function highlightMentions(content: unknown): React.ReactNode {
  const text = extractText(content)
  const parts = text.split(/(@\w+)/g)
  return parts.map((part, idx) =>
    part.startsWith('@') ? (
      <span key={idx} className="px-1.5 py-0.5 bg-cyan-900 text-cyan-200 rounded font-medium">
        {part}
      </span>
    ) : (
      part
    )
  )
}

function MentionHighlighter({ content }: { content: unknown }) {
  return <>{highlightMentions(content)}</>
}

export function MessageList({ channel }: Props) {
  const query = useMessages(channel)
  const agentMap = useAgentMap()
  const deleteMessage = useDeleteMessage(channel)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [query.data])

  return (
    <QueryState {...query} empty={<div className="text-neutral-500">No messages</div>}>
      {(messages) => (
        <div className="space-y-4">
          {messages.map((msg: Message) => (
            <div
              key={msg.message_id}
              className="border-b border-neutral-800 pb-4 relative group"
              onMouseEnter={() => setHoveredId(msg.message_id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="font-semibold text-cyan-400">
                  {agentMap.get(msg.agent_id) ?? msg.agent_id.slice(0, 7)}
                </span>
                <span className="text-xs text-neutral-500">
                  {new Date(msg.created_at).toLocaleTimeString()}
                </span>
                {hoveredId === msg.message_id && (
                  <button
                    onClick={() => deleteMessage.mutate(msg.message_id)}
                    className="ml-auto text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                    title="Delete message"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z" />
                      <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z" />
                    </svg>
                  </button>
                )}
              </div>
              <div className="text-neutral-300 text-sm prose prose-invert prose-sm max-w-none prose-strong:text-white prose-headings:text-white prose-p:my-2 prose-li:my-1">
                <Markdown
                  components={{
                    p: ({ children }) => (
                      <p>
                        <MentionHighlighter content={children} />
                      </p>
                    ),
                    strong: ({ children }) => (
                      <strong>
                        <MentionHighlighter content={children} />
                      </strong>
                    ),
                    em: ({ children }) => (
                      <em>
                        <MentionHighlighter content={children} />
                      </em>
                    ),
                  }}
                >
                  {msg.content}
                </Markdown>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}
    </QueryState>
  )
}
