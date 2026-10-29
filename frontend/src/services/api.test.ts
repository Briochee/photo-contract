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
})
