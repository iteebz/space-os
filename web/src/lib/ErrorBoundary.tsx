import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error) {
    console.error('ErrorBoundary caught:', error)
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <div className="p-4 text-red-400">
            <h2 className="font-bold mb-2">Error</h2>
            <pre className="text-sm">{this.state.error.message}</pre>
          </div>
        )
      )
    }
    return this.props.children
  }
}
