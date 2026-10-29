import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../services/api'
import { ClientDetailPage } from './ClientDetailPage'

vi.mock('../services/api', () => ({
  api: {
    client: vi.fn(),
    updateClient: vi.fn(),
    createAgreement: vi.fn(),
    acceptAgreement: vi.fn(),
    deleteAgreement: vi.fn(),
    generateDocument: vi.fn(),
  },
}))

const clientRecord = {
  id: 12,
  legal_name: 'Example Client',
  display_name: null,
  mailing_address: '',
  primary_contact_name: '',
  primary_contact_title: '',
  contact_email: '',
  contact_phone: '',
  notes: '',
  created_at: '2026-10-29T12:00:00',
  updated_at: '2026-10-29T12:00:00',
  bookings: [],
  invoices: [],
  agreements: [
    {
      id: 3,
      agreement_ref: 'AGR-2026-003',
      client_id: 12,
      client_name: 'Example Client',
      effective_date: '2026-10-29',
      status: 'draft' as const,
      template_version: '1.0.0',
      legal_text_hash: 'abc123',
      accepted_at: null,
      acceptance_reference: '',
    },
  ],
}

describe('ClientDetailPage agreement actions', () => {
  beforeEach(() => {
    vi.mocked(api.client).mockResolvedValue(clientRecord)
    vi.mocked(api.deleteAgreement).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => vi.restoreAllMocks())

  it('offers a delete action for an agreement that is not linked to a booking', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/clients/12']}>
          <Routes>
            <Route path="/clients/:clientId" element={<ClientDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await user.click(await screen.findByRole('button', { name: 'Delete agreement AGR-2026-003' }))

    await waitFor(() => expect(api.deleteAgreement).toHaveBeenCalledWith(3))
    expect(window.confirm).toHaveBeenCalledWith(
      expect.stringContaining('Any generated PDF copies remain in Documents.'),
    )
  })
})
