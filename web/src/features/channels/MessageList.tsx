import Markdown from 'react-markdown'
import { useMessages } from './hooks'
import { useAgents } from '../agents'
import type { Message } from './types'

interface Props {
  channel: string
}

export function MessageList({ channel }: Props) {
  const { data: messages, isLoading, error } = useMessages(channel)
  const { data: agents } = useAgents()

  const agentMap = new Map(agents?.map((a) => [a.agent_id, a.identity]) ?? [])

  if (isLoading) return <div className="text-neutral-500">Loading...</div>
  if (error) return <div className="text-red-500">Error loading messages</div>
  if (!messages?.length) return <div className="text-neutral-500">No messages</div>

  return (
    <div className="space-y-4">
      {messages.map((msg: Message) => (
        <div key={msg.message_id} className="border-b border-neutral-800 pb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-cyan-400">
              {agentMap.get(msg.agent_id) ?? msg.agent_id.slice(0, 7)}
            </span>
            <span className="text-xs text-neutral-500">
              {new Date(msg.created_at).toLocaleTimeString()}
            </span>
          </div>
          <div className="text-neutral-300 text-sm prose prose-invert prose-sm max-w-none prose-strong:text-white prose-headings:text-white prose-p:my-2 prose-li:my-1">
            <Markdown>{msg.content}</Markdown>
          </div>
        </div>
      ))}
    </div>
  )
}
