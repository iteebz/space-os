import { useEffect, useState, useCallback } from 'react'
import type { Agent } from '../agents/types'
import type { Channel } from './types'

interface Suggestion {
  value: string
  label: string
  description?: string
}

interface Props {
  value: string
  cursorPosition: number
  agents: Agent[]
  channels: Channel[]
  onSelect: (completion: string) => void
  onDismiss: () => void
}

const CONTROL_COMMANDS: Suggestion[] = [
  { value: '!pause', label: '!pause', description: 'Pause running spawns (reversible)' },
  { value: '!resume', label: '!resume', description: 'Resume paused spawns' },
  { value: '!abort', label: '!abort', description: 'Kill running spawns (permanent)' },
]

export function DelimiterAutocomplete({
  value,
  cursorPosition,
  agents,
  channels,
  onSelect,
  onDismiss,
}: Props) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [triggerChar, setTriggerChar] = useState<string | null>(null)

  useEffect(() => {
    const beforeCursor = value.slice(0, cursorPosition)
    const match = beforeCursor.match(/[@!#]([\w-]*)$/)

    if (!match) {
      setSuggestions([])
      setTriggerChar(null)
      return
    }

    const [fullMatch, query] = match
    const trigger = fullMatch[0]
    setTriggerChar(trigger)

    let filtered: Suggestion[] = []

    if (trigger === '@') {
      filtered = agents
        .filter((a) => a.identity.toLowerCase().includes(query.toLowerCase()))
        .map((a) => ({
          value: a.identity,
          label: a.identity,
          description: a.role || undefined,
        }))
    } else if (trigger === '!') {
      filtered = CONTROL_COMMANDS.filter((cmd) =>
        cmd.value.toLowerCase().includes(query.toLowerCase())
      )
    } else if (trigger === '#') {
      filtered = channels
        .filter((c) => c.name.toLowerCase().includes(query.toLowerCase()))
        .map((c) => ({
          value: c.name,
          label: c.name,
          description: c.topic || undefined,
        }))
    }

    setSuggestions(filtered)
    setSelectedIndex(0)
  }, [value, cursorPosition, agents, channels])

  const handleSelect = useCallback(
    (value: string) => {
      if (!triggerChar) return
      onSelect(`${triggerChar}${value}`)
    },
    [triggerChar, onSelect]
  )

  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (suggestions.length === 0) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % suggestions.length)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length)
      } else if ((e.key === 'Enter' || e.key === 'Tab') && suggestions.length > 0) {
        e.preventDefault()
        handleSelect(suggestions[selectedIndex].value)
      } else if (e.key === 'Escape') {
        e.preventDefault()
        onDismiss()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [suggestions, selectedIndex, handleSelect, onDismiss])

  if (suggestions.length === 0) return null

  return (
    <div className="absolute bottom-full left-0 mb-2 w-full max-w-md bg-neutral-900 border border-neutral-700 rounded shadow-lg overflow-hidden z-50">
      <ul className="max-h-64 overflow-y-auto">
        {suggestions.map((suggestion, i) => (
          <li key={suggestion.value}>
            <button
              onClick={() => handleSelect(suggestion.value)}
              className={`w-full text-left px-3 py-2 text-sm ${
                i === selectedIndex
                  ? 'bg-cyan-600 text-white'
                  : 'text-neutral-300 hover:bg-neutral-800'
              }`}
            >
              <div className="font-medium">
                {triggerChar}
                {suggestion.label}
              </div>
              {suggestion.description && (
                <div className="text-xs text-neutral-400 mt-0.5">{suggestion.description}</div>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
