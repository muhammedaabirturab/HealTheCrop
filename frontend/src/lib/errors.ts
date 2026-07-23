import { isAxiosError } from 'axios'
import type { TFunction } from 'i18next'

/**
 * Turns any error thrown by an API call into a translated, user-meaningful message.
 *
 * Without this, every form in the app just showed a blanket "something went wrong"
 * for everything from a dropped Wi-Fi connection to an expired session to a genuine
 * validation mistake — which reads as a broken app rather than a helpful one. This
 * distinguishes: no response at all (network/CORS), 401 (session expired), 422
 * (FastAPI/Pydantic validation errors, which arrive as an array of {msg} objects),
 * a plain string `detail` from an HTTPException, and anything else (server fault).
 */
export function getErrorMessage(error: unknown, t: TFunction): string {
  if (!isAxiosError(error)) {
    return t('errors.generic')
  }

  if (!error.response) {
    return t('errors.network')
  }

  const { status, data } = error.response
  const detail = (data as { detail?: unknown } | undefined)?.detail

  if (status === 401) {
    return t('errors.sessionExpired')
  }

  if (status === 422) {
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : null))
        .filter(Boolean)
      if (messages.length > 0) return messages.join(' ')
    }
    return t('errors.validation')
  }

  if (typeof detail === 'string' && detail.length > 0) {
    return detail
  }

  if (status >= 500) {
    return t('errors.generic')
  }

  return t('errors.generic')
}

export function isSessionExpired(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 401
}
