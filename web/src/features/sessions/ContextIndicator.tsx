import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../../lib/api'

interface UsageData {
  input_tokens: number
  output_tokens: number
  context_used: number
  context_limit: number
  percentage: number
  model: string
}

interface Props {
  sessionId: string
}

function getBarColor(percentage: number): string {
  if (percentage < 50) return 'bg-neutral-600'
  if (percentage < 80) return 'bg-yellow-500'
  return 'bg-red-500'
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${Math.round(n / 1000)}k`
  return String(n)
}

export function ContextIndicator({ sessionId }: Props) {
  const { data } = useQuery<UsageData>({
    queryKey: ['session-usage', sessionId],
    queryFn: () => fetchApi(`/sessions/${sessionId}/usage`),
    refetchInterval: 2000,
    staleTime: 1000,
  })

  if (!data || data.context_used === 0) return null

  const { percentage, context_used, context_limit } = data
  const barColor = getBarColor(percentage)

  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-neutral-500 mb-1">
        <span>
          {formatTokens(context_used)} / {formatTokens(context_limit)}
        </span>
        <span>{percentage}%</span>
      </div>
      <div className="h-1 bg-neutral-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
