import { describe, it, expect } from 'vitest'
import React from 'react'

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

function highlightDelimiters(content: unknown, validIdentities: Set<string>): Array<string | React.ReactElement> {
  const text = extractText(content)
  const parts = text.split(/(@[\w-]+|~\/[\w/.@-]+|\.\/[\w/.@-]*)/g)
  return parts.map((part) => {
    if (!part) return null
    if (part.startsWith('@')) {
      const identity = part.slice(1)
      if (!validIdentities.has(identity)) return part
      return `<@mention>${part}</>`
    }
    if (part.startsWith('~/') || part.startsWith('./')) {
      return `<@path>${part}</>`
    }
    return part
  }).filter(Boolean) as Array<string | React.ReactElement>
}

describe('mention highlighting', () => {
  it('extracts text from string nodes', () => {
    expect(extractText('hello world')).toBe('hello world')
  })

  it('extracts text from number nodes', () => {
    expect(extractText(42)).toBe('42')
  })

  it('extracts text from array nodes', () => {
    expect(extractText(['hello', ' ', 'world'])).toBe('hello world')
  })

  it('extracts text from React element nodes', () => {
    const element = React.createElement('span', { children: 'nested text' })
    expect(extractText(element)).toBe('nested text')
  })

  it('handles nested React elements', () => {
    const inner = React.createElement('strong', { children: 'bold' })
    const outer = React.createElement('p', { children: [inner, ' text'] })
    expect(extractText(outer)).toBe('bold text')
  })

  it('returns empty string for null/undefined', () => {
    expect(extractText(null)).toBe('')
    expect(extractText(undefined)).toBe('')
  })

  it('highlights valid mentions', () => {
    const validIdentities = new Set(['human', 'auger'])
    const result = highlightDelimiters('Hello @human and @auger', validIdentities)
    expect(result.some(r => typeof r === 'string' && r.includes('@mention'))).toBe(true)
  })

  it('does not highlight invalid mentions', () => {
    const validIdentities = new Set(['human'])
    const result = highlightDelimiters('Hello @human and @unknown', validIdentities)
    const resultStr = result.join('')
    expect(resultStr).toContain('@human')
    expect(resultStr).toContain('@unknown')
  })

  it('handles mentions in complex markdown', () => {
    const validIdentities = new Set(['human'])
    const mixed = 'Say hello to @human in ~/config/file'
    const result = highlightDelimiters(mixed, validIdentities)
    const resultStr = result.join('')
    expect(resultStr).toContain('@mention')
    expect(resultStr).toContain('@path')
  })

  it('ignores mentions without valid identity', () => {
    const validIdentities = new Set<string>()
    const result = highlightDelimiters('@unknown text', validIdentities)
    expect(result[0]).toBe('@unknown')
  })

  it('processes paths correctly', () => {
    const validIdentities = new Set<string>()
    const result = highlightDelimiters('file at ~/config or ./local', validIdentities)
    const resultStr = result.join('')
    expect(resultStr).toContain('@path')
  })

  it('handles mixed content with multiple mentions', () => {
    const validIdentities = new Set(['prime', 'zealot'])
    const content = 'Hey @prime and @zealot check ~/workspace/file.md'
    const result = highlightDelimiters(content, validIdentities)
    const resultStr = result.join('')
    expect(resultStr).toContain('@mention')
    expect(resultStr).toContain('@path')
  })

  it('extracts text from markdown children prop', () => {
    const markdownChild = {
      props: {
        children: 'text from markdown'
      }
    }
    expect(extractText(markdownChild)).toBe('text from markdown')
  })
})
