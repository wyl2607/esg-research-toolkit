import { describe, expect, it } from 'vitest'
import type { TFunction } from 'i18next'
import { ApiError } from './api'
import { isBackendOffline, localizeErrorMessage } from './error-utils'

// Fake translator: returns the key (plus interpolation values) so tests
// assert key selection without loading i18next.
const t = ((key: string, opts?: Record<string, unknown>) =>
  opts ? `${key}:${JSON.stringify(opts)}` : key) as unknown as TFunction

describe('isBackendOffline', () => {
  it('is true for fetch-level network failures', () => {
    expect(isBackendOffline(new TypeError('Failed to fetch'))).toBe(true)
  })

  it.each([502, 503, 504])('is true for gateway status %i', (status) => {
    expect(isBackendOffline(new ApiError(status, 'gateway'))).toBe(true)
  })

  it('is false for client errors and non-errors', () => {
    expect(isBackendOffline(new ApiError(404, 'not found'))).toBe(false)
    expect(isBackendOffline(new ApiError(500, 'boom'))).toBe(false)
    expect(isBackendOffline('offline')).toBe(false)
    expect(isBackendOffline(undefined)).toBe(false)
  })

  it('parses a status embedded in a plain Error message', () => {
    expect(isBackendOffline(new Error('Request failed: 503'))).toBe(true)
    expect(isBackendOffline(new Error('Request failed: 400'))).toBe(false)
  })
})

describe('localizeErrorMessage', () => {
  it.each([
    [401, 'errors.unauthorized'],
    [403, 'errors.unauthorized'],
    [404, 'errors.notFound'],
    [408, 'errors.timeout'],
    [429, 'errors.rateLimited'],
    [502, 'errors.backendOffline'],
    [503, 'errors.backendOffline'],
    [504, 'errors.backendOffline'],
  ])('maps ApiError %i to %s', (status, key) => {
    expect(localizeErrorMessage(t, new ApiError(status, 'detail'))).toBe(key)
  })

  it('maps other 5xx to serverError with the status interpolated', () => {
    expect(localizeErrorMessage(t, new ApiError(500, 'boom'))).toBe(
      'errors.serverError:{"status":500}'
    )
  })

  it('maps network failures to networkError', () => {
    expect(localizeErrorMessage(t, new TypeError('Failed to fetch'))).toBe('errors.networkError')
  })

  it('falls back for non-errors and unrecognized statuses', () => {
    expect(localizeErrorMessage(t, 'nope')).toBe('errors.unknown')
    expect(localizeErrorMessage(t, new Error('no status here'))).toBe('errors.unknown')
    expect(localizeErrorMessage(t, new ApiError(418, 'teapot'))).toBe('errors.unknown')
  })

  it('honors a custom fallback key', () => {
    expect(localizeErrorMessage(t, new Error('nope'), 'errors.uploadFailed')).toBe(
      'errors.uploadFailed'
    )
  })
})
