import React, { useState, useRef } from 'react'
import { useSendMessage, useHumanIdentity } from './hooks'
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
  const [uploadedImages, setUploadedImages] = useState<string[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const textareaRef = useRef<globalThis.HTMLTextAreaElement>(null)
  const fileInputRef = useRef<globalThis.HTMLInputElement>(null)
  const { data: identityData } = useHumanIdentity()
  const humanIdentity = identityData?.identity
  const { mutate: send, isPending } = useSendMessage(channel, humanIdentity)
  const { data: agents = [] } = useAgents()
  const { data: channels = [] } = useChannels()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim() || isPending) return

    let messageContent = content.trim()
    if (uploadedImages.length > 0) {
      const imagePaths = uploadedImages.map((path) => `Image: ${path}`).join('\n')
      messageContent = `${imagePaths}\n\n${messageContent}`
    }

    send(messageContent, {
      onSuccess: () => {
        setContent('')
        setUploadedImages([])
        setShowAutocomplete(false)
      },
    })
  }

  const handleFileSelect = async (e: React.ChangeEvent<globalThis.HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setIsUploading(true)
      const formData = new globalThis.FormData()
      formData.append('file', file)

      const response = await fetch('http://localhost:8000/api/upload/image', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('Upload failed')

      const data = await response.json()
      setUploadedImages((prev) => [...prev, data.path])
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Image upload failed:', error)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleRemoveImage = (index: number) => {
    setUploadedImages((prev) => prev.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showAutocomplete && ['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) {
      return
    }

    if (e.key === 'Enter') {
      if (e.shiftKey) {
        return
      }
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

      {uploadedImages.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {uploadedImages.map((path, index) => (
            <div
              key={index}
              className="relative bg-neutral-800 rounded px-2 py-1 text-xs text-neutral-300 flex items-center gap-2"
            >
              <span className="truncate max-w-xs">{path.split('/').pop()}</span>
              <button
                type="button"
                onClick={() => handleRemoveImage(index)}
                className="text-red-400 hover:text-red-300"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isPending || isUploading}
          className="px-3 py-2 bg-neutral-800 border border-neutral-700 rounded text-neutral-400 hover:text-neutral-200 hover:border-neutral-600 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Attach image"
        >
          {isUploading ? '...' : '📎'}
        </button>

        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={`Message #${channel}... (@mention !command #channel)`}
          className="flex-1 bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm text-neutral-200 placeholder-neutral-500 resize-none focus:outline-none focus:border-cyan-500"
          rows={3}
          disabled={isPending}
        />
      </div>
    </form>
  )
}
