import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../services/api'
import type { Settings } from '../types'
import { SettingsPage } from './SettingsPage'

vi.mock('../services/api', () => ({ api: { settings: vi.fn(), updateSettings: vi.fn() } }))

const settings: Settings = {
  profile: {
    legal_name: '',
    business_name: null,
    mailing_address: '',
    email: '',
    phone: '',
    payment_instructions: '',
    default_payment_terms_days: null,
    currency: 'USD',
    default_photography_rate: null,
    default_overtime_rate: null,
    default_delivery_method: null,
    default_delivery_deadline: null,
  },
  output_directory: '/tmp/photo-contract/documents',
  preferences: { pdf_page_size: 'Letter' },
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.mocked(api.settings).mockResolvedValue(settings)
    vi.mocked(api.updateSettings).mockResolvedValue(settings)
  })

  it('loads and saves a profile with no business name or optional defaults', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <SettingsPage />
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    expect(screen.getByLabelText('Business name (optional)')).toHaveValue('')
    expect(screen.getByLabelText('Default photography rate ($, optional)')).toHaveValue(null)
    expect(screen.getByLabelText('Default payment terms (calendar days, optional)')).toHaveValue(
      null,
    )

    await user.type(screen.getByLabelText('Photographer legal name'), 'Riley Photographer')
    await user.click(screen.getByRole('button', { name: 'Save settings' }))

    await waitFor(() =>
      expect(api.updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          legal_name: 'Riley Photographer',
          business_name: null,
          default_payment_terms_days: null,
          default_photography_rate: null,
          default_overtime_rate: null,
          default_delivery_method: null,
          default_delivery_deadline: null,
        }),
      ),
    )
  })
})
