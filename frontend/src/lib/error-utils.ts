import type { TFunction } from 'i18next'
import { ApiError } from './api'

function extractStatus(error: Error): number | null {
  if (error instanceof ApiError) return error.status
  const m = error.message.match(/\b(\d{3})\b/)
  return m ? Number(m[1]) : null
}

/** Returns true when the backend server is unreachable or returning 5xx gateway errors. */
export function isBackendOffline(error: unknown): boolean {
  if (error instanceof Error) {
    if (error.message.includes('Failed to fetch')) return true
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return true
    const status = extractStatus(error)
    if (status != null && (status === 502 || status === 503 || status === 504)) return true
  }
  return false
}

export function localizeErrorMessage(
  t: TFunction,
  error: unknown,
  fallbackKey: string = 'errors.unknown'
): string {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) {
    return t('errors.networkError')
  }

  if (!(error instanceof Error)) return t(fallbackKey)

  if (error.message.includes('Failed to fetch')) {
    return t('errors.networkError')
  }

  const status = extractStatus(error)
  if (status == null) return t(fallbackKey)
  if (status === 401 || status === 403) return t('errors.unauthorized')
  if (status === 404) return t('errors.notFound')
  if (status === 408) return t('errors.timeout')
  if (status === 429) return t('errors.rateLimited')
  if (status === 502 || status === 503 || status === 504) return t('errors.backendOffline')
  if (status >= 500) return t('errors.serverError', { status })

  return t(fallbackKey)
}
