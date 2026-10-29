export type Client = {
  id: number
  legal_name: string
  display_name: string | null
  mailing_address: string
  primary_contact_name: string
  primary_contact_title: string
  contact_email: string
  contact_phone: string
  notes: string
  created_at: string
  updated_at: string
}

export type LineItem = {
  id?: number
  description: string
  quantity: string
  unit: string
  unit_rate: string
  unit_rate_cents: number
  amount: string
  amount_cents: number
  category?: string
  authorization_status?: 'proposed' | 'approved' | 'rejected' | null
  authorization_date?: string | null
  authorization_reference?: string
  notes?: string
  source_booking_line_item_id?: number | null
  source_expense_id?: number | null
}

export type LineItemInput = {
  description: string
  quantity: string
  unit: string
  unit_rate: string
  category?: string
}

export type ExpenseInput = LineItemInput & {
  authorization_status: 'proposed' | 'approved' | 'rejected'
  authorization_date: string | null
  authorization_reference: string
  notes: string
}

export type Booking = {
  id: number
  booking_ref: string
  client_id: number
  client: Client
  agreement_id: number | null
  agreement_date: string | null
  event_name: string
  event_type: string
  event_date: string
  venue: string
  venue_address: string
  coverage_start: string
  coverage_end: string
  coverage_hours: string
  scope: string
  delivery_method: string
  delivery_deadline: string
  special_deliverables: string
  guaranteed_image_count: number | null
  overtime_rate: string
  overtime_rate_cents: number
  payment_terms_days: number
  exceptions: string
  status: 'draft' | 'accepted' | 'cancelled'
  accepted_at: string | null
  acceptance_reference: string
  line_items: LineItem[]
  additional_expenses: LineItem[]
  subtotal_cents: number
  subtotal: string
  approved_expenses_total_cents: number
  total_chargeable_cents: number
  amendments: Amendment[]
  invoices?: Array<{ id: number; invoice_ref: string; status: string; version: number }>
  created_at: string
  updated_at: string
}

export type Amendment = {
  id: number
  reference: string
  change_summary: string
  changes: Record<string, unknown>
  status: string
  written_acceptance_date: string | null
  acceptance_reference: string
}

export type Invoice = {
  id: number
  invoice_ref: string
  booking_id: number
  booking_ref: string
  client: Client
  event_name: string
  event_date: string
  version: number
  revision_of_id: number | null
  replaced_by_id: number | null
  is_current: boolean
  invoice_date: string
  due_date: string
  status: 'draft' | 'issued' | 'partially_paid' | 'paid' | 'overdue' | 'voided'
  record_status: 'draft' | 'issued' | 'voided'
  tax_mode: 'none' | 'rate' | 'manual'
  tax_rate: string
  line_items: LineItem[]
  subtotal_cents: number
  tax_cents: number
  total_cents: number
  amount_paid_cents: number
  balance_due_cents: number
  notes: string
  payments: Payment[]
  created_at: string
  issued_at: string | null
}

export type Payment = {
  id: number
  paid_at: string
  amount_cents: number
  amount: string
  method: string
  reference: string
  notes: string
}

export type Agreement = {
  id: number
  agreement_ref: string
  client_id: number
  client_name: string
  effective_date: string
  status: 'draft' | 'accepted'
  template_version: string
  legal_text_hash: string
  accepted_at: string | null
  acceptance_reference: string
}

export type GeneratedDocument = {
  id: number
  document_type: 'agreement' | 'booking_confirmation' | 'invoice'
  name: string
  client_id: number
  client_name: string
  booking_id: number | null
  booking_reference: string | null
  invoice_id: number | null
  invoice_reference: string | null
  reference: string
  version: number
  status: 'draft' | 'final'
  created_at: string
  content_hash: string
  template_version: string
}

export type Profile = {
  legal_name: string
  business_name: string | null
  mailing_address: string
  email: string
  phone: string
  payment_instructions: string
  default_payment_terms_days: number | null
  currency: 'USD'
  default_photography_rate: string | null
  default_overtime_rate: string | null
  default_delivery_method: string | null
  default_delivery_deadline: string | null
}

export type Settings = {
  profile: Profile
  output_directory: string
  preferences: { pdf_page_size: string }
}

export type Dashboard = {
  active_bookings: number
  upcoming_assignments: Array<{
    id: number
    booking_ref: string
    event_name: string
    event_date: string
    client_name: string
    status: string
  }>
  draft_invoices: number
  outstanding_invoices: number
  outstanding_balance_cents: number
  recent_clients: Array<{ id: number; legal_name: string; display_name: string | null }>
  recent_documents: Array<{
    id: number
    document_type: string
    reference: string
    version: number
    created_at: string
    status: string
  }>
}

export type DocumentRequest = {
  document_type: GeneratedDocument['document_type']
  entity_id: number
}

export type BookingPayload = Omit<
  Booking,
  | 'id'
  | 'booking_ref'
  | 'client'
  | 'agreement_date'
  | 'status'
  | 'accepted_at'
  | 'acceptance_reference'
  | 'subtotal_cents'
  | 'subtotal'
  | 'amendments'
  | 'invoices'
  | 'created_at'
  | 'updated_at'
  | 'overtime_rate_cents'
  | 'line_items'
  | 'additional_expenses'
> & {
  line_items: LineItemInput[]
  additional_expenses: ExpenseInput[]
}

export type InvoicePayload = {
  booking_id: number
  invoice_date: string
  due_date: string
  tax_mode: 'none' | 'rate' | 'manual'
  tax_rate: string
  manual_tax: string
  notes: string
  line_items: Array<{
    source_booking_line_item_id: number | null
    source_expense_id: number | null
    description: string
    quantity: string
    unit: string
    unit_rate: string
  }>
}
