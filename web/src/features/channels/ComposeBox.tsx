import React, { useState, useRef, useEffect } from 'react'
import { BsArrowUp, BsPlus } from 'react-icons/bs'
import { useSendMessage, useHumanIdentity } from './hooks'
import { useAgents } from '../agents'
import { useChannels } from './hooks'
import { DelimiterAutocomplete } from './DelimiterAutocomplete'

interface Props {
  channel: string
}

export function ComposeBox({ channel }: Props) {
  const [drafts, setDrafts] = useState<Map<string, string>>(() => {
    const stored = localStorage.getItem('space-os:drafts')
    return stored ? new Map(JSON.parse(stored)) : new Map()
  })
  const [cursorPosition, setCursorPosition] = useState(0)
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [uploadedImages, setUploadedImages] = useState<Map<string, string[]>>(() => {
    const stored = localStorage.getItem('space-os:images')
    return stored ? new Map(JSON.parse(stored)) : new Map()
  })

  const content = drafts.get(channel) ?? ''
  const setContent = (value: string) => setDrafts((prev) => {
    const updated = new Map(prev).set(channel, value)
    localStorage.setItem('space-os:drafts', JSON.stringify(Array.from(updated.entries())))
    return updated
  })
  const currentImages = uploadedImages.get(channel) ?? []
  const setCurrentImages = (images: string[]) =>
    setUploadedImages((prev) => {
      const updated = new Map(prev).set(channel, images)
      localStorage.setItem('space-os:images', JSON.stringify(Array.from(updated.entries())))
      return updated
    })
  const [isUploading, setIsUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
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
    if (currentImages.length > 0) {
      const imagePaths = currentImages.map((path) => `Image: ${path}`).join('\n')
      messageContent = `${imagePaths}\n\n${messageContent}`
    }

    send(messageContent, {
      onSuccess: () => {
        setContent('')
        setCurrentImages([])
        setShowAutocomplete(false)
        textareaRef.current?.focus()
      },
    })
  }

  const uploadFile = async (file: globalThis.File) => {
    try {
      setIsUploading(true)
      const formData = new globalThis.FormData()
      formData.append('file', file)

      const response = await fetch('/api/upload/image', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('Upload failed')

      const data = await response.json()
      setCurrentImages([...currentImages, data.path])
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Image upload failed:', error)
    } finally {
      setIsUploading(false)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<globalThis.HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    await uploadFile(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleRemoveImage = (index: number) => {
    setCurrentImages(currentImages.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showAutocomplete && ['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) {
      return
    }

    if (e.key === 'Enter') {
      if (e.shiftKey) {
        e.preventDefault()
        handleSubmit(e)
      }
    }
  }

  const handleChange = (e: React.ChangeEvent<globalThis.HTMLTextAreaElement>) => {
    const newValue = e.target.value
    const newCursor = e.target.selectionStart
    setContent(newValue)
    setCursorPosition(newCursor)

    const beforeCursor = newValue.slice(0, newCursor)
    const hasDelimiter = /[@!#/][\w-]*$/.test(beforeCursor)
    setShowAutocomplete(hasDelimiter)
  }

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [content])

  const handleAutocompleteSelect = (completion: string) => {
    if (!textareaRef.current) return

    const beforeCursor = content.slice(0, cursorPosition)
    const afterCursor = content.slice(cursorPosition)
    const match = beforeCursor.match(/[@!#/][\w-]*$/)

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

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    if (e.currentTarget === e.target) setIsDragging(false)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) {
      await uploadFile(file)
    }
  }

  const handlePaste = async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return

    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (file) await uploadFile(file)
        break
      }
    }
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

      {currentImages.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {currentImages.map((path, index) => (
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

      <div className="flex gap-2 items-end relative">
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
          className="w-10 h-10 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center text-neutral-400 hover:text-white hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
          title="Attach image"
        >
          {isUploading ? '...' : <BsPlus size={20} />}
        </button>
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onPaste={handlePaste}
          placeholder={`Message #${channel}`}
          className={`flex-1 bg-neutral-900 border rounded-xl px-3 py-2.5 text-base text-neutral-200 placeholder-neutral-500 resize-none focus:outline-none transition-colors max-h-[200px] overflow-y-auto min-h-0 ${
            isDragging
              ? 'border-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.3)]'
              : 'border-neutral-700 focus:border-cyan-500'
          }`}
          disabled={isPending}
          rows={1}
        />
        <button
          type="submit"
          disabled={!content.trim() || isPending}
          className="w-10 h-10 rounded-full flex items-center justify-center transition-colors shrink-0 disabled:opacity-50 disabled:cursor-not-allowed bg-cyan-600 hover:bg-cyan-500 disabled:bg-neutral-800 text-white disabled:text-neutral-600"
          title="Send message"
        >
          <BsArrowUp size={20} />
        </button>
      </div>
    </form>
  )
}
