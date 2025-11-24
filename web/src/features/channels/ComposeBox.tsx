import React, { useState, useRef } from 'react'
import { useSendMessage } from './hooks'
import { useAgents } from '../agents'
import { useChannels } from './hooks'
import { DelimiterAutocomplete } from './DelimiterAutocomplete'

interface Props {
  channel: string
}

export function ComposeBox({ channel }: Props) {
  const [content, setContent] = useState('')
  const [cursorPosition, setCursorPosition] = useState(0)
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const textareaRef = useRef<globalThis.HTMLTextAreaElement>(null)
  const { mutate: send, isPending } = useSendMessage(channel)
  const { data: agents = [] } = useAgents()
  const { data: channels = [] } = useChannels()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim() || isPending) return
    send(content.trim())
    setContent('')
    setShowAutocomplete(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showAutocomplete && ['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) {
      return
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleChange = (e: React.ChangeEvent<globalThis.HTMLTextAreaElement>) => {
    const newValue = e.target.value
    const newCursor = e.target.selectionStart
    setContent(newValue)
    setCursorPosition(newCursor)

    const beforeCursor = newValue.slice(0, newCursor)
    const hasDelimiter = /[@!#][\w-]*$/.test(beforeCursor)
    setShowAutocomplete(hasDelimiter)
  }

  const handleAutocompleteSelect = (completion: string) => {
    if (!textareaRef.current) return

    const beforeCursor = content.slice(0, cursorPosition)
    const afterCursor = content.slice(cursorPosition)
    const match = beforeCursor.match(/[@!#][\w-]*$/)

    if (!match) return

    const newContent = beforeCursor.slice(0, match.index) + completion + ' ' + afterCursor
    setContent(newContent)
    setShowAutocomplete(false)

    globalThis.setTimeout(() => {
      const newCursor = (match.index || 0) + completion.length + 1
      textareaRef.current?.setSelectionRange(newCursor, newCursor)
      textareaRef.current?.focus()
    }, 0)
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-neutral-800 pt-4 relative">
      {showAutocomplete && (
        <DelimiterAutocomplete
          value={content}
          cursorPosition={cursorPosition}
          agents={agents}
          channels={channels}
          onSelect={handleAutocompleteSelect}
          onDismiss={() => setShowAutocomplete(false)}
        />
      )}
      <textarea
        ref={textareaRef}
        value={content}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={`Message #${channel}... (@mention !command #channel)`}
        className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm text-neutral-200 placeholder-neutral-500 resize-none focus:outline-none focus:border-cyan-500"
        rows={3}
        disabled={isPending}
      />
    </form>
  )
}
