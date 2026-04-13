import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ESG Toolkit error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-64 flex-col items-center justify-center space-y-4">
          <div className="text-5xl text-red-500">⚠️</div>
          <h2 className="text-lg font-semibold text-slate-800">Something went wrong</h2>
          <p className="max-w-md text-center text-sm text-slate-500">{this.state.message}</p>
          <button
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
            onClick={() => this.setState({ hasError: false, message: '' })}
            type="button"
          >
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
