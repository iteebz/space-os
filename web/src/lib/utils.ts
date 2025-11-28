import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Parse UTC timestamp and format as local time.
 * Backend stores timestamps without timezone info (assumes UTC).
 */
export function formatLocalTime(utcTimestamp: string): string {
  const isoString = utcTimestamp.endsWith('Z') ? utcTimestamp : `${utcTimestamp}Z`
  return new Date(isoString).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export function formatLocalDate(utcTimestamp: string): string {
  const isoString = utcTimestamp.endsWith('Z') ? utcTimestamp : `${utcTimestamp}Z`
  return new Date(isoString).toLocaleDateString()
}

export function formatLocalDateTime(utcTimestamp: string): string {
  const isoString = utcTimestamp.endsWith('Z') ? utcTimestamp : `${utcTimestamp}Z`
  return new Date(isoString).toLocaleString()
}
