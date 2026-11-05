import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../services/api'
import { DocumentsPage } from './DocumentsPage'

vi.mock('../services/api', () => ({
  api: {
    documents: vi.fn(),
    deleteDocument: vi.fn(),
    downloadUrl: vi.fn((id: number) => `/api/documents/${id}/download`),
    documentPreviewUrl: vi.fn((id: number) => `/api/documents/${id}/preview`),
  },
}))

describe('DocumentsPage', () => {
  beforeEach(() => {
    vi.mocked(api.documents).mockResolvedValue([
      {
        id: 2,
        document_type: 'booking_confirmation',
        name: 'BK-2026-002_Booking-Confirmation_v1.pdf',
        client_id: 4,
        client_name: 'Example Client',
        booking_id: 2,
        booking_reference: 'BK-2026-002',
        invoice_id: null,
        invoice_reference: null,
        reference: 'BK-2026-002',
        version: 1,
        status: 'draft',
        created_at: '2026-10-29T12:00:00',
        content_hash: 'abc123',
        template_version: '1.0.0',
      },
    ])
    vi.mocked(api.deleteDocument).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => vi.restoreAllMocks())

  it('deletes a selected library PDF after confirmation', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await user.click(
      await screen.findByRole('button', {
        name: 'Delete BK-2026-002_Booking-Confirmation_v1.pdf',
      }),
    )

    await waitFor(() => expect(vi.mocked(api.deleteDocument).mock.calls[0]?.[0]).toBe(2))
    expect(window.confirm).toHaveBeenCalledWith(
      expect.stringContaining('Permanently delete BK-2026-002_Booking-Confirmation_v1.pdf'),
    )
  })

  it('shows the original as finalized and nests its signed copy beneath it', async () => {
    vi.mocked(api.documents).mockResolvedValue([
      {
        id: 8,
        document_type: 'agreement',
        name: 'AGR-2026-005_Signed-Copy_v2.pdf',
        client_id: 4,
        client_name: 'Example Client',
        booking_id: null,
        booking_reference: null,
        invoice_id: null,
        invoice_reference: null,
        reference: 'AGR-2026-005',
        version: 2,
        status: 'final',
        created_at: '2026-11-05T12:00:00',
        content_hash: 'signed-hash',
        template_version: 'signed-pdf-upload',
      },
      {
        id: 7,
        document_type: 'agreement',
        name: 'AGR-2026-005_Master-Agreement_v1.pdf',
        client_id: 4,
        client_name: 'Example Client',
        booking_id: null,
        booking_reference: null,
        invoice_id: null,
        invoice_reference: null,
        reference: 'AGR-2026-005',
        version: 1,
        status: 'pending',
        created_at: '2026-11-04T12:00:00',
        content_hash: 'original-hash',
        template_version: '1.0.0',
      },
    ])
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DocumentsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const originalRow = (await screen.findByText('AGR-2026-005_Master-Agreement_v1.pdf')).closest(
      'tr',
    )
    const signedRow = screen.getByText('AGR-2026-005_Signed-Copy_v2.pdf').closest('tr')

    expect(originalRow).toHaveTextContent('Finalized')
    expect(signedRow).toHaveClass('document-row--signed-copy')
    expect(signedRow).toHaveTextContent('↳')
    expect(signedRow).toHaveTextContent('Signed copy of AGR-2026-005_Master-Agreement_v1.pdf')
    expect(originalRow?.nextElementSibling).toBe(signedRow)
  })
})
