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
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
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
                    className="ml-auto text-xs text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete message"
                  >
                    delete
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
