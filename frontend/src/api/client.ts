/**
 * Client HTTP de Tier Fist.
 *
 * L'authentification repose sur un cookie de session HttpOnly posé par Django :
 * aucun token n'est stocké côté navigateur (spec §6.2). Les requêtes mutantes
 * renvoient le token CSRF lu dans le cookie non-HttpOnly prévu pour cela.
 */

export class ApiError extends Error {
  status: number
  code?: string
  errors?: Record<string, unknown>

  constructor(status: number, message: string, code?: string, errors?: Record<string, unknown>) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.errors = errors
  }
}

const CSRF_COOKIE = 'tierfist_csrftoken'

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`))
  return match ? decodeURIComponent(match[2]) : null
}

let csrfPrimed = false

async function ensureCsrfToken(): Promise<string | null> {
  const existing = readCookie(CSRF_COOKIE)
  if (existing) return existing
  if (!csrfPrimed) {
    csrfPrimed = true
    await fetch('/api/auth/csrf', { credentials: 'include' })
  }
  return readCookie(CSRF_COOKIE)
}

interface RequestOptions {
  method?: string
  body?: unknown
  /** Envoi multipart pour les uploads d'images. */
  formData?: FormData
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = {}
  let body: BodyInit | undefined

  if (options.formData) {
    body = options.formData
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = await ensureCsrfToken()
    if (token) headers['X-CSRFToken'] = token
  }

  const response = await fetch(path, { method, headers, body, credentials: 'include' })

  if (response.status === 204) return undefined as T

  const contentType = response.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json') ? await response.json() : null

  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload?.detail ?? 'Une erreur est survenue. Laurent enquête.',
      payload?.code,
      payload?.errors,
    )
  }
  return payload as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  postForm: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: 'POST', formData }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  patchForm: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: 'PATCH', formData }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
