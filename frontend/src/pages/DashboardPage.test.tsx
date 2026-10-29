import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DashboardPage } from './DashboardPage'
import { api } from '../services/api'

vi.mock('../services/api', () => ({ api: { dashboard: vi.fn() } }))

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.mocked(api.dashboard).mockResolvedValue({
      active_bookings: 2,
      upcoming_assignments: [
        {
          id: 7,
          booking_ref: 'BK-2026-007',
          event_name: 'Annual meeting',
          event_date: '2026-11-20',
          client_name: 'Example Corporation',
          status: 'finalized',
        },
      ],
      draft_invoices: 1,
      outstanding_invoices: 1,
      outstanding_balance_cents: 83_000,
      recent_clients: [{ id: 4, legal_name: 'Example Corporation', display_name: 'Example' }],
      recent_documents: [],
    })
  })

  it('shows actionable booking and financial summaries from the API', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('heading', { name: 'Good work, in focus.' })).toBeInTheDocument()
    expect(await screen.findByText('Annual meeting')).toBeInTheDocument()
    expect(screen.getByText('$830.00')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'New booking' })).toHaveAttribute(
      'href',
      '/bookings/new',
    )
  })
})
