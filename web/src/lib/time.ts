export function formatRelativeTime(isoTimestamp: string | null): string {
  if (!isoTimestamp) return 'never'

  const date = new Date(isoTimestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'now'
  if (diffMins < 60) return `${diffMins}m`

  const isToday = now.toDateString() === date.toDateString()
  if (isToday) return `${diffHours}h`

  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (yesterday.toDateString() === date.toDateString()) return 'yesterday'

  if (diffDays < 7) {
    return date.toLocaleDateString('en-US', { weekday: 'short' })
  }

  const isThisYear = now.getFullYear() === date.getFullYear()
  if (isThisYear) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatDateDivider(isoTimestamp: string): string {
  const date = new Date(isoTimestamp)
  const now = new Date()

  const isToday = now.toDateString() === date.toDateString()
  if (isToday) return 'Today'

  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (yesterday.toDateString() === date.toDateString()) return 'Yesterday'

  return date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
}

export function isSameDay(date1: string, date2: string): boolean {
  return new Date(date1).toDateString() === new Date(date2).toDateString()
}
