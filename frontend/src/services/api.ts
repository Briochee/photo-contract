import type {
  Agreement,
  Booking,
  BookingPayload,
  Client,
  DataResetResult,
  Dashboard,
  DocumentRequest,
  ExpenseInput,
  GeneratedDocument,
  Invoice,
  InvoicePayload,
  Profile,
  Settings,
} from '../types'

function errorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) return fallback
  const detail = payload.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((issue) => {
      if (!issue || typeof issue !== 'object') return []
      const message = 'msg' in issue && typeof issue.msg === 'string' ? issue.msg : null
      if (!message) return []
      const location =
        'loc' in issue && Array.isArray(issue.loc)
          ? issue.loc.filter(
              (part: unknown): part is string => typeof part === 'string' && part !== 'body',
            )
          : []
      return [`${location.length ? `${location.join('.')}: ` : ''}${message}`]
    })
    if (messages.length) return messages.join('; ')
  }
  if (detail && typeof detail === 'object') {
    const message = 'message' in detail ? detail.message : 'msg' in detail ? detail.msg : null
    if (typeof message === 'string' && message.trim()) return message
    return JSON.stringify(detail) || fallback
  }
  return fallback
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(errorMessage(payload, `Request failed (${response.status})`))
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

const json = (method: string, value?: unknown): RequestInit => ({
  method,
  ...(value === undefined ? {} : { body: JSON.stringify(value) }),
})

export const api = {
  dashboard: () => request<Dashboard>('/api/dashboard'),
  clients: (q = '') => request<Client[]>(`/api/clients${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  client: (id: number) =>
    request<Client & { bookings: Booking[]; invoices: Invoice[]; agreements: Agreement[] }>(
      `/api/clients/${id}`,
    ),
  createClient: (value: Partial<Client>) => request<Client>('/api/clients', json('POST', value)),
  updateClient: (id: number, value: Partial<Client>) =>
    request<Client>(`/api/clients/${id}`, json('PATCH', value)),
  bookings: () => request<Booking[]>('/api/bookings'),
  booking: (id: number) => request<Booking>(`/api/bookings/${id}`),
  createBooking: (value: BookingPayload) => request<Booking>('/api/bookings', json('POST', value)),
  updateBooking: (id: number, value: BookingPayload) =>
    request<Booking>(`/api/bookings/${id}`, json('PATCH', value)),
  deleteBooking: (id: number) => request<void>(`/api/bookings/${id}`, json('DELETE')),
  acceptBooking: (id: number, value: { accepted_date: string; acceptance_reference: string }) =>
    request<Booking>(`/api/bookings/${id}/accept`, json('POST', value)),
  addExpense: (id: number, value: ExpenseInput) =>
    request(`/api/bookings/${id}/expenses`, json('POST', value)),
  authorizeExpense: (
    bookingId: number,
    expenseId: number,
    value: {
      authorization_status: 'proposed' | 'approved' | 'rejected'
      authorization_date: string | null
      authorization_reference: string
      notes: string
    },
  ) => request(`/api/bookings/${bookingId}/expenses/${expenseId}`, json('PATCH', value)),
  amendments: (
    id: number,
    value: {
      change_summary: string
      changes: Record<string, unknown>
      written_acceptance_date?: string
      acceptance_reference?: string
      accepted: boolean
    },
  ) => request(`/api/bookings/${id}/amendments`, json('POST', value)),
  invoices: () => request<Invoice[]>('/api/invoices'),
  invoice: (id: number) => request<Invoice>(`/api/invoices/${id}`),
  createInvoice: (value: InvoicePayload) => request<Invoice>('/api/invoices', json('POST', value)),
  updateInvoice: (id: number, value: InvoicePayload) =>
    request<Invoice>(`/api/invoices/${id}`, json('PATCH', value)),
  issueInvoice: (id: number) => request<Invoice>(`/api/invoices/${id}/issue`, json('POST')),
  addPayment: (
    id: number,
    value: { paid_at: string; amount: string; method: string; reference: string; notes: string },
  ) => request<Invoice>(`/api/invoices/${id}/payments`, json('POST', value)),
  reviseInvoice: (id: number) => request<Invoice>(`/api/invoices/${id}/revisions`, json('POST')),
  agreements: () => request<Agreement[]>('/api/agreements'),
  createAgreement: (value: {
    client_id: number
    effective_date: string
    accepted: boolean
    accepted_date?: string
    acceptance_reference?: string
  }) => request<Agreement>('/api/agreements', json('POST', value)),
  acceptAgreement: (id: number, value: { accepted_date: string; acceptance_reference: string }) =>
    request<Agreement>(`/api/agreements/${id}/accept`, json('POST', value)),
  deleteAgreement: (id: number) => request<void>(`/api/agreements/${id}`, json('DELETE')),
  settings: () => request<Settings>('/api/settings'),
  updateSettings: (value: Profile) => request<Settings>('/api/settings', json('PATCH', value)),
  clearAllData: () =>
    request<DataResetResult>(
      '/api/settings/data',
      json('DELETE', { confirmation: 'CLEAR_ALL_DATA' }),
    ),
  documents: () => request<GeneratedDocument[]>('/api/documents'),
  deleteDocument: (id: number) => request<void>(`/api/documents/${id}`, json('DELETE')),
  previewDocument: async (value: DocumentRequest) => {
    const response = await fetch('/api/documents/preview', json('POST', value))
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(errorMessage(payload, `Preview failed (${response.status})`))
    }
    return URL.createObjectURL(await response.blob())
  },
  generateDocument: (value: DocumentRequest) =>
    request<GeneratedDocument>('/api/documents/generate', json('POST', value)),
  downloadUrl: (id: number) => `/api/documents/${id}/download`,
  documentPreviewUrl: (id: number) => `/api/documents/${id}/preview`,
}
