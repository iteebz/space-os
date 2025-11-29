import { parseDiff, Diff, Hunk } from 'react-diff-view'
import { createTwoFilesPatch } from 'diff'
import stripAnsi from 'strip-ansi'
import 'react-diff-view/style/index.css'

interface BashCallProps {
  command: string
  description?: string
}

export function BashCall({ command, description }: BashCallProps) {
  return (
    <div className="space-y-1">
      {description && <div className="text-xs text-neutral-500">{description}</div>}
      <div className="font-mono text-sm text-cyan-400">$ {command}</div>
    </div>
  )
}

interface BashResultProps {
  output: string
  is_error: boolean
}

export function BashResult({ output, is_error }: BashResultProps) {
  const clean = stripAnsi(output)
  const lines = clean.split('\n')
  const maxLines = is_error ? 50 : 25
  const truncated = lines.length > maxLines
  const displayed = lines.slice(0, maxLines).join('\n')

  return (
    <div className="space-y-1">
      <pre
        className={`font-mono text-xs overflow-auto max-h-96 ${is_error ? 'text-red-400' : 'text-neutral-400'}`}
      >
        {displayed}
      </pre>
      {truncated && (
        <div className="text-xs text-neutral-600">+{lines.length - maxLines} more lines</div>
      )}
    </div>
  )
}

interface EditCallProps {
  file_path: string
  edits?: Array<{ old_string: string; new_string: string }>
  old_string?: string
  new_string?: string
}

export function EditCall({ file_path, edits, old_string, new_string }: EditCallProps) {
  const editList = edits || (old_string && new_string ? [{ old_string, new_string }] : [])

  if (!editList.length) {
    return <div className="text-xs text-neutral-500">{file_path} - No edits</div>
  }

  const firstEdit = editList[0]
  const diffText = createTwoFilesPatch(
    file_path,
    file_path,
    firstEdit.old_string,
    firstEdit.new_string,
    '',
    '',
    { context: 3 }
  )
  const [diff] = parseDiff(diffText, { nearbySequences: 'zip' })

  return (
    <div className="space-y-1">
      <div className="text-xs text-neutral-500">
        {file_path}
        {editList.length > 1 && <span className="ml-2">({editList.length} edits)</span>}
      </div>
      <div className="text-xs overflow-auto max-h-96 bg-neutral-900 rounded">
        {diff && diff.hunks.length > 0 ? (
          <Diff viewType="split" diffType="modify" hunks={diff.hunks}>
            {(hunks) => hunks.map((hunk) => <Hunk key={hunk.content} hunk={hunk} />)}
          </Diff>
        ) : (
          <div className="p-2 text-neutral-500">No diff to display</div>
        )}
      </div>
    </div>
  )
}

interface GenericToolProps {
  name: string
  input: unknown
}

interface MetadataResultProps {
  output: string
}

function getFilePath(params: Record<string, unknown>): string | null {
  return (params.file_path ?? params.path ?? null) as string | null
}

function formatPath(path: string): { filename: string; dir: string } {
  const parts = path.split('/')
  const filename = parts.pop() || path
  const dir = parts.slice(-2).join('/') || '/'
  return { filename, dir }
}

export function ReadCall({ input }: { input: Record<string, unknown> }) {
  const path = getFilePath(input)
  if (!path) return <div className="text-cyan-400 text-sm">Read</div>

  const { filename, dir } = formatPath(path)
  const offset = input.offset as number | undefined
  const limit = input.limit as number | undefined
  const range = offset || limit ? ` [${offset ?? 0}:${limit ? `+${limit}` : ''}]` : ''

  return (
    <div>
      <div className="text-cyan-400 text-sm">
        Read {filename}
        {range}
      </div>
      <div className="text-neutral-600 text-xs">{dir}</div>
    </div>
  )
}

export function WriteCall({ input }: { input: Record<string, unknown> }) {
  const path = getFilePath(input)
  if (!path) return <div className="text-cyan-400 text-sm">Write</div>

  const { filename, dir } = formatPath(path)
  const content = input.content as string | undefined
  const preview = content ? content.slice(0, 80).replace(/\n/g, '↵') : null

  return (
    <div>
      <div className="text-cyan-400 text-sm">Write {filename}</div>
      <div className="text-neutral-600 text-xs">{dir}</div>
      {preview && (
        <div className="text-neutral-500 text-xs font-mono mt-1 truncate">
          {preview}
          {content && content.length > 80 ? '...' : ''}
        </div>
      )}
    </div>
  )
}

export function GrepCall({ input }: { input: Record<string, unknown> }) {
  const pattern = input.pattern as string | undefined
  const path = input.path as string | undefined
  const glob = input.glob as string | undefined
  const type = input.type as string | undefined

  let scope = ''
  if (path) scope = ` in ${formatPath(path).filename}`
  else if (glob) scope = ` (${glob})`
  else if (type) scope = ` (*.${type})`

  return (
    <div className="text-cyan-400 text-sm">
      Grep <span className="text-yellow-400">"{pattern}"</span>
      {scope}
    </div>
  )
}

export function GlobCall({ input }: { input: Record<string, unknown> }) {
  const pattern = input.pattern as string | undefined
  const path = input.path as string | undefined
  const scope = path ? ` in ${formatPath(path).filename}` : ''

  return (
    <div className="text-cyan-400 text-sm">
      Glob <span className="text-yellow-400">"{pattern}"</span>
      {scope}
    </div>
  )
}

export function LSCall({ input }: { input: Record<string, unknown> }) {
  const path = input.path as string | undefined
  if (!path) return <div className="text-cyan-400 text-sm">LS</div>

  const { filename, dir } = formatPath(path)
  return (
    <div>
      <div className="text-cyan-400 text-sm">LS {filename || '/'}</div>
      {dir !== '/' && <div className="text-neutral-600 text-xs">{dir}</div>}
    </div>
  )
}

export function GenericTool({ name, input }: GenericToolProps) {
  const params = input as Record<string, unknown>
  const path = getFilePath(params)
  const command = params.command as string | undefined

  let display = name
  let detail: string | null = null

  if (path) {
    const { filename, dir } = formatPath(path)
    display = `${name} ${filename}`
    detail = dir
  } else if (command) {
    const cmdStr = String(command)
    display = `${name}: ${cmdStr.slice(0, 60)}${cmdStr.length > 60 ? '...' : ''}`
  }

  return (
    <div>
      <div className="text-cyan-400 text-sm">{display}</div>
      {detail && <div className="text-neutral-600 text-xs">{detail}</div>}
    </div>
  )
}

export function MetadataResult({ output }: MetadataResultProps) {
  const lines = output.split('\n').filter((l) => l.trim())
  const chars = output.length
  const kb = (chars / 1024).toFixed(1)

  return (
    <div className="text-xs text-neutral-600">
      {lines.length} lines · {kb} KB
    </div>
  )
}
