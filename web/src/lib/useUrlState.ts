import { useCallback, useSyncExternalStore } from 'react'

function getSnapshot() {
  return window.location.search
}

function subscribe(callback: () => void) {
  window.addEventListener('popstate', callback)
  return () => window.removeEventListener('popstate', callback)
}

export function useUrlState() {
  const search = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
  const params = new URLSearchParams(search)

  const setParam = useCallback((key: string, value: string | null) => {
    const currentParams = new URLSearchParams(window.location.search)
    const currentValue = currentParams.get(key)

    if (currentValue === value) return

    if (value === null) {
      currentParams.delete(key)
    } else {
      currentParams.set(key, value)
    }
    const newUrl = `${window.location.pathname}?${currentParams.toString()}`
    window.history.pushState({}, '', newUrl)
    window.dispatchEvent(new globalThis.PopStateEvent('popstate'))
  }, [])

  return { params, setParam }
}
