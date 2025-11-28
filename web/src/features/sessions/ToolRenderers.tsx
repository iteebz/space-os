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
  const maxLines = is_error ? 50 : 10
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

export function GenericTool({ name, input }: GenericToolProps) {
  const params = input as Record<string, unknown>
  let display = name

  if (name === 'Read' && params.file_path) {
    display = `Read ${String(params.file_path).split('/').pop()}`
  } else if (name === 'Write' && params.file_path) {
    display = `Write ${String(params.file_path).split('/').pop()}`
  } else if (name === 'Grep' && params.pattern) {
    display = `Grep "${params.pattern}"`
  } else if (name === 'Glob' && params.pattern) {
    display = `Glob "${params.pattern}"`
  } else if (name === 'LS' && params.path) {
    display = `LS ${String(params.path).split('/').pop()}`
  } else if (params.file_path) {
    display = `${name} ${String(params.file_path).split('/').pop()}`
  }

  return <div className="text-cyan-400 text-sm">{display}</div>
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
