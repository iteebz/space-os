import Markdown from 'react-markdown'
import { useMessages } from './hooks'
import { useAgentMap } from '../agents'
import { QueryState } from '../../lib/QueryState'
import type { Message } from './types'

interface Props {
  channel: string
}

export function MessageList({ channel }: Props) {
  const query = useMessages(channel)
  const agentMap = useAgentMap()

  return (
    <QueryState {...query} empty={<div className="text-neutral-500">No messages</div>}>
      {(messages) => (
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
      )}
    </QueryState>
  )
}
