import { Component, type ErrorInfo, type ReactNode } from 'react'
import i18n from '@/i18n'
import { localizeErrorMessage } from '@/lib/error-utils'

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
    return {
      hasError: true,
      message: localizeErrorMessage(i18n.t.bind(i18n), error, 'errors.unknown'),
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ESG Toolkit UI error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex h-64 flex-col items-center justify-center space-y-4 px-6 text-center"
          role="alert"
          aria-live="assertive"
        >
          <div className="text-5xl text-red-500">⚠️</div>
          <h2 className="text-lg font-semibold text-slate-800">
            {i18n.t('errorBoundary.title')}
          </h2>
          <p className="max-w-md text-sm text-slate-500">{this.state.message}</p>
          <p className="max-w-md text-xs text-slate-400">{i18n.t('errorBoundary.suggestion')}</p>
          <button
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            onClick={() => this.setState({ hasError: false, message: '' })}
            type="button"
          >
            {i18n.t('errorBoundary.retry')}
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
