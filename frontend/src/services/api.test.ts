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

  it('uploads signed booking confirmations as PDF with the signature date', async () => {
    const file = new File(['%PDF-signed'], 'signed confirmation.pdf', {
      type: 'application/pdf',
    })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'finalized' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await api.uploadSignedBookingConfirmation(12, '2026-11-05', file)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/bookings/12/signed-copy?signed_date=2026-11-05&filename=signed+confirmation.pdf',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/pdf' },
        body: file,
      },
    )
  })

  it('attaches related files without changing the source record', async () => {
    const file = new File(['%PDF-receipt'], 'receipt copy.pdf', { type: 'application/pdf' })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ related_entity_type: 'invoice', related_entity_id: 8 }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await api.attachDocument('invoice', 8, file)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/documents/attach?entity_type=invoice&entity_id=8&filename=receipt+copy.pdf',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/pdf' },
        body: file,
      },
    )
  })
})
