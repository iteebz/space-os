const API_BASE = '/api'

export async function api<T>(endpoint: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, init)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const fetchApi = <T>(endpoint: string) => api<T>(endpoint)

export const postApi = <T>(endpoint: string, data: unknown) =>
  api<T>(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const patchApi = <T>(endpoint: string, data: unknown) =>
  api<T>(endpoint, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const deleteApi = <T>(endpoint: string) => api<T>(endpoint, { method: 'DELETE' })

export const postApiNoBody = <T>(endpoint: string) => api<T>(endpoint, { method: 'POST' })
