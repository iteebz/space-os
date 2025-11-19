import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { postApi } from '../../lib/api'

export function CreateChannel() {
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState('')
  const [topic, setTopic] = useState('')
  const queryClient = useQueryClient()

  const { mutate, isPending } = useMutation({
    mutationFn: () => postApi('/channels', { name, topic: topic || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
      setName('')
      setTopic('')
      setIsOpen(false)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || isPending) return
    mutate()
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="w-full text-left px-2 py-1 text-sm text-neutral-500 hover:text-white hover:bg-neutral-800/50 rounded mb-2"
      >
        + New channel
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4 space-y-2">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="channel-name"
        className="w-full bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-cyan-500"
        autoFocus
      />
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Topic (optional)"
        className="w-full bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-cyan-500"
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={isPending || !name.trim()}
          className="px-2 py-1 text-xs bg-cyan-600 text-white rounded hover:bg-cyan-500 disabled:opacity-50"
        >
          Create
        </button>
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          className="px-2 py-1 text-xs text-neutral-400 hover:text-white"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
