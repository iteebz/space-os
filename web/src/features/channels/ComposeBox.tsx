import React, { useState } from 'react'
import { useSendMessage } from './hooks'

interface Props {
  channel: string
}

export function ComposeBox({ channel }: Props) {
  const [content, setContent] = useState('')
  const { mutate: send, isPending } = useSendMessage(channel)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim() || isPending) return
    send(content.trim())
    setContent('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-neutral-800 pt-4">
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={`Message #${channel}... (Enter to send, Shift+Enter for newline)`}
        className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm text-neutral-200 placeholder-neutral-500 resize-none focus:outline-none focus:border-cyan-500"
        rows={3}
        disabled={isPending}
      />
    </form>
  )
}
