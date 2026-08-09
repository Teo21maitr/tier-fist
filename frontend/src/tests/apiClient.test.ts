import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from '../api/client'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('client API', () => {
  beforeEach(() => {
    document.cookie = 'tierfist_csrftoken=jeton-de-test'
  })

  it('envoie les cookies de session sur chaque requête', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    await api.get('/api/auth/me')

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: 'include' })
  })

  it("joint l'en-tête CSRF aux requêtes mutantes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await api.post('/api/tier-lists', { name: 'X', theme: 'Y' })

    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers['X-CSRFToken']).toBe('jeton-de-test')
    expect(init.method).toBe('POST')
  })

  it("n'ajoute pas d'en-tête CSRF sur une lecture", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)

    await api.get('/api/tier-lists')

    expect(fetchMock.mock.calls[0][1].headers['X-CSRFToken']).toBeUndefined()
  })

  it('remonte le message et le code métier en cas d’erreur', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: 'Pas ton tour.', code: 'not_your_turn' }, 403),
      ),
    )

    await expect(api.post('/api/tier-lists/1/joker/use')).rejects.toMatchObject({
      message: 'Pas ton tour.',
      code: 'not_your_turn',
      status: 403,
    })
  })

  it('gère une réponse 204 sans corps', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(api.delete('/api/tier-lists/1')).resolves.toBeUndefined()
  })

  it('ne sérialise pas un FormData en JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    const formData = new FormData()
    formData.append('name', 'KFC')
    await api.postForm('/api/tier-lists/1/items', formData)

    const [, init] = fetchMock.mock.calls[0]
    expect(init.body).toBeInstanceOf(FormData)
    expect(init.headers['Content-Type']).toBeUndefined()
  })

  it('expose une erreur typée', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'Non' }, 400)))
    await expect(api.get('/api/x')).rejects.toBeInstanceOf(ApiError)
  })
})
