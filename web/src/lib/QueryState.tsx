import type { ReactNode } from 'react'

interface Props<T> {
  isLoading: boolean
  error: unknown
  data: T | undefined
  children: (data: T) => ReactNode
  empty?: ReactNode
}

export function QueryState<T>({ isLoading, error, data, children, empty }: Props<T>) {
  if (isLoading) return <div className="text-neutral-500">Loading...</div>
  if (error) return <div className="text-red-500">Error loading data</div>
  if (!data || (Array.isArray(data) && data.length === 0)) {
    return <>{empty ?? <div className="text-neutral-500">No data</div>}</>
  }
  return <>{children(data)}</>
}
