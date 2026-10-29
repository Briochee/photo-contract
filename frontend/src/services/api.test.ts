import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

describe('preview API errors', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('formats FastAPI validation errors instead of showing object stringification', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({
          detail: [{ loc: ['body', 'entity_id'], msg: 'Input should be greater than 0' }],
        }),
      }),
    )

    await expect(api.previewDocument({ document_type: 'agreement', entity_id: 0 })).rejects.toThrow(
      'entity_id: Input should be greater than 0',
    )
  })

  it('sends preview requests as JSON', async () => {
    const request = { document_type: 'agreement' as const, entity_id: 12 }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['%PDF-preview'], { type: 'application/pdf' }),
    })
    const createObjectURL = vi.fn().mockReturnValue('blob:agreement-preview')
    vi.stubGlobal('fetch', fetchMock)
    vi.stubGlobal('URL', { createObjectURL })

    await expect(api.previewDocument(request)).resolves.toBe('blob:agreement-preview')

    expect(fetchMock).toHaveBeenCalledWith('/api/documents/preview', {
      method: 'POST',
      body: JSON.stringify(request),
      headers: { 'Content-Type': 'application/json' },
    })
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob))
  })
})
