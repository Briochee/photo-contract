import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../services/api'
import { InvoicesPage } from './InvoicesPage'

vi.mock('../services/api', () => ({ api: { invoices: vi.fn() } }))

describe('InvoicesPage', () => {
  beforeEach(() => {
    vi.mocked(api.invoices).mockResolvedValue([])
  })

  it('offers invoice creation without requiring an accepted booking', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <InvoicesPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByText(/any saved booking/i)).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Create invoice' })[0]).toHaveAttribute(
      'href',
      '/invoices/new',
    )
  })
})
