import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useFieldArray, useForm, useWatch } from 'react-hook-form'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { PdfPreview } from '../components/common/PdfPreview'
import {
  ErrorMessage,
  FieldError,
  Loading,
  PageHeader,
  Panel,
  Status,
} from '../components/common/Ui'
import { api } from '../services/api'
import { invoiceSchema } from '../schemas'
import type { InvoicePayload } from '../types'
import { dateLabel, money, todayIso } from '../utils/format'
import { calculateTaxCents, decimalToCents, lineAmountCents } from '../utils/money'

type FormInput = z.input<typeof invoiceSchema>
type Values = z.output<typeof invoiceSchema>

function invoicePayload(value: Values): InvoicePayload {
  return {
    ...value,
    line_items: value.line_items.map(
      ({
        source_booking_line_item_id,
        source_expense_id,
        description,
        quantity,
        unit,
        unit_rate,
      }) => ({
        source_booking_line_item_id,
        source_expense_id,
        description,
        quantity,
        unit,
        unit_rate,
      }),
    ),
  }
}

function addDays(iso: string, days: number): string {
  const result = new Date(`${iso}T12:00:00`)
  result.setDate(result.getDate() + days)
  const local = new Date(result.getTime() - result.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}

export function InvoiceEditorPage() {
  const invoiceId = Number(useParams().invoiceId) || null
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const initialBookingId = Number(params.get('booking')) || 0
  const invoiceQuery = useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => api.invoice(invoiceId!),
    enabled: Boolean(invoiceId),
  })
  const bookings = useQuery({ queryKey: ['bookings'], queryFn: api.bookings })
  const form = useForm<FormInput, unknown, Values>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: {
      booking_id: initialBookingId,
      invoice_date: todayIso(),
      due_date: todayIso(),
      tax_mode: 'none',
      tax_rate: '0',
      manual_tax: '0',
      notes: '',
      line_items: [],
    },
  })
  const bookingId = Number(useWatch({ control: form.control, name: 'booking_id' })) || 0
  const bookingQuery = useQuery({
    queryKey: ['booking', bookingId],
    queryFn: () => api.booking(bookingId),
    enabled: bookingId > 0,
  })
  const lineArray = useFieldArray({ control: form.control, name: 'line_items' })
  const lines = useWatch({ control: form.control, name: 'line_items' }) ?? []
  const taxMode = useWatch({ control: form.control, name: 'tax_mode' })
  const taxRate = useWatch({ control: form.control, name: 'tax_rate' }) ?? '0'
  const manualTax = useWatch({ control: form.control, name: 'manual_tax' }) ?? '0'
  const [paymentDate, setPaymentDate] = useState(todayIso())
  const [paymentAmount, setPaymentAmount] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('')
  const [paymentReference, setPaymentReference] = useState('')
  const [paymentNotes, setPaymentNotes] = useState('')
  const [lastGeneratedName, setLastGeneratedName] = useState('')

  useEffect(() => {
    if (invoiceQuery.data) {
      const invoice = invoiceQuery.data
      form.reset({
        booking_id: invoice.booking_id,
        invoice_date: invoice.invoice_date,
        due_date: invoice.due_date,
        tax_mode: invoice.tax_mode,
        tax_rate: invoice.tax_mode === 'manual' ? '0' : invoice.tax_rate,
        manual_tax: invoice.tax_mode === 'manual' ? invoice.tax_rate : '0',
        notes: invoice.notes,
        line_items: invoice.line_items.map((item) => ({
          description: item.description,
          quantity: item.quantity,
          unit: item.unit,
          unit_rate: item.unit_rate,
          category: item.category ?? 'service',
          source_booking_line_item_id: item.source_booking_line_item_id ?? null,
          source_expense_id: item.source_expense_id ?? null,
        })),
      })
    } else if (!invoiceId && bookingQuery.data) {
      const booking = bookingQuery.data
      form.reset({
        booking_id: booking.id,
        invoice_date: todayIso(),
        due_date: addDays(todayIso(), booking.payment_terms_days),
        tax_mode: 'none',
        tax_rate: '0',
        manual_tax: '0',
        notes: '',
        line_items: [
          ...booking.line_items.map((item) => ({
            description: item.description,
            quantity: item.quantity,
            unit: item.unit,
            unit_rate: item.unit_rate,
            category: item.category ?? 'service',
            source_booking_line_item_id: item.id!,
            source_expense_id: null,
          })),
          ...booking.additional_expenses
            .filter((item) => item.authorization_status === 'approved')
            .map((item) => ({
              description: item.description,
              quantity: item.quantity,
              unit: item.unit,
              unit_rate: item.unit_rate,
              category: 'expense',
              source_booking_line_item_id: null,
              source_expense_id: item.id!,
            })),
        ],
      })
    }
  }, [bookingQuery.data, form, invoiceId, invoiceQuery.data])

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ['invoices'] })
    await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    if (invoiceId) await queryClient.invalidateQueries({ queryKey: ['invoice', invoiceId] })
    if (bookingId) await queryClient.invalidateQueries({ queryKey: ['booking', bookingId] })
  }
  const save = useMutation({
    mutationFn: (value: Values) =>
      invoiceId
        ? api.updateInvoice(invoiceId, invoicePayload(value))
        : api.createInvoice(invoicePayload(value)),
    onSuccess: async (invoice) => {
      await invalidate()
      navigate(`/invoices/${invoice.id}`)
    },
  })
  const issue = useMutation({
    mutationFn: () => api.issueInvoice(invoiceId!),
    onSuccess: async (issued) => {
      await invalidate()
      try {
        const document = await api.generateDocument({
          document_type: 'invoice',
          entity_id: issued.id,
        })
        setLastGeneratedName(document.name)
        await queryClient.invalidateQueries({ queryKey: ['documents'] })
      } catch (error) {
        setLastGeneratedName(
          error instanceof Error
            ? `Invoice issued; PDF generation needs attention: ${error.message}`
            : 'Invoice issued; PDF generation needs attention.',
        )
      }
    },
  })
  const payment = useMutation({
    mutationFn: () =>
      api.addPayment(invoiceId!, {
        paid_at: paymentDate,
        amount: paymentAmount,
        method: paymentMethod,
        reference: paymentReference,
        notes: paymentNotes,
      }),
    onSuccess: async () => {
      setPaymentAmount('')
      await invalidate()
    },
  })
  const revision = useMutation({
    mutationFn: () => api.reviseInvoice(invoiceId!),
    onSuccess: async (value) => {
      await invalidate()
      navigate(`/invoices/${value.id}`)
    },
  })
  const generated = useMutation({
    mutationFn: () => api.generateDocument({ document_type: 'invoice', entity_id: invoiceId! }),
    onSuccess: async (document) => {
      setLastGeneratedName(document.name)
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  if (
    (invoiceId && invoiceQuery.isLoading) ||
    bookings.isLoading ||
    (bookingId > 0 && bookingQuery.isLoading)
  )
    return <Loading />
  const invoice = invoiceQuery.data
  const booking = bookingQuery.data
  const locked = invoice?.record_status === 'issued' || invoice?.record_status === 'voided'
  const subtotalCents = lines.reduce(
    (sum, line) => sum + lineAmountCents(line.quantity, line.unit_rate),
    0,
  )
  const calculatedTax = calculateTaxCents(subtotalCents, taxMode, taxRate, manualTax)

  return (
    <>
      <PageHeader
        eyebrow="Invoice / Financial record"
        title={invoice?.invoice_ref ?? 'Create invoice'}
        description={
          invoice
            ? `${invoice.client.legal_name} · ${invoice.booking_ref}`
            : 'Import agreed charges from an accepted booking.'
        }
        action={
          <Link className="button button--quiet" to="/invoices">
            ← Invoices
          </Link>
        }
      />
      <div className="stack">
        <ErrorMessage
          error={
            invoiceQuery.error ||
            bookings.error ||
            bookingQuery.error ||
            save.error ||
            issue.error ||
            payment.error ||
            revision.error ||
            generated.error
          }
        />
        {invoice && (
          <div className="record-banner">
            <div>
              <span className="eyebrow">Invoice reference</span>
              <strong>{invoice.invoice_ref}</strong>
            </div>
            <Status value={invoice.status} />
            <span className="muted">Booking {invoice.booking_ref}</span>
          </div>
        )}
        <form className="stack" onSubmit={form.handleSubmit((value) => save.mutate(value))}>
          <fieldset className="form-fieldset" disabled={Boolean(locked)}>
            <Panel shadow>
              <div className="section-heading">
                <h2>Invoice details</h2>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="booking_id">Accepted booking *</label>
                  <select id="booking_id" {...form.register('booking_id', { valueAsNumber: true })}>
                    <option value={0}>Select booking</option>
                    {bookings.data
                      ?.filter((item) => item.status === 'accepted')
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.booking_ref} · {item.event_name}
                        </option>
                      ))}
                  </select>
                  {form.formState.errors.booking_id && (
                    <FieldError>{form.formState.errors.booking_id.message}</FieldError>
                  )}
                </div>
                <div className="field">
                  <label htmlFor="invoice_date">Invoice date</label>
                  <input id="invoice_date" type="date" {...form.register('invoice_date')} />
                </div>
                <div className="field">
                  <label htmlFor="due_date">
                    Due date · follows accepted Net {booking?.payment_terms_days ?? '15'} terms
                  </label>
                  <input id="due_date" type="date" {...form.register('due_date')} />
                </div>
              </div>
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>Itemized charges</h2>
                <span className="muted">Source charges are locked to the accepted booking</span>
              </div>
              {!booking && (
                <p className="muted">Select an accepted booking to load its agreed charges.</p>
              )}
              <div className="line-list" role="group" aria-label="Invoice line items">
                <div className="invoice-line-row invoice-line-row--head">
                  <span>Item</span>
                  <span>Quantity</span>
                  <span className="numeric">Rate</span>
                  <span className="numeric">Amount</span>
                  <span>Order</span>
                </div>
                {lineArray.fields.map((field, index) => {
                  const isBase = lines[index]?.source_booking_line_item_id != null
                  return (
                    <div className="invoice-line-row" key={field.id}>
                      <input
                        type="hidden"
                        {...form.register(`line_items.${index}.source_booking_line_item_id`, {
                          setValueAs: (value) => (value === '' ? null : Number(value)),
                        })}
                      />
                      <input
                        type="hidden"
                        {...form.register(`line_items.${index}.source_expense_id`, {
                          setValueAs: (value) => (value === '' ? null : Number(value)),
                        })}
                      />
                      <span>
                        {lines[index]?.description}
                        <small className="table-subline">
                          {isBase ? 'Accepted booking charge' : 'Approved additional expense'}
                        </small>
                      </span>
                      <span>
                        {lines[index]?.quantity} {lines[index]?.unit}
                      </span>
                      <span className="numeric">
                        {money(decimalToCents(lines[index]?.unit_rate ?? '0'))}
                      </span>
                      <span className="numeric">
                        {money(
                          lineAmountCents(
                            lines[index]?.quantity ?? '0',
                            lines[index]?.unit_rate ?? '0',
                          ),
                        )}
                      </span>
                      <span className="line-actions">
                        <button
                          type="button"
                          className="text-button"
                          disabled={index === 0}
                          onClick={() => lineArray.move(index, index - 1)}
                          aria-label={`Move invoice line ${index + 1} up`}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          className="text-button"
                          disabled={index === lineArray.fields.length - 1}
                          onClick={() => lineArray.move(index, index + 1)}
                          aria-label={`Move invoice line ${index + 1} down`}
                        >
                          ↓
                        </button>
                        {!isBase && (
                          <button
                            type="button"
                            className="text-button text-button--danger"
                            onClick={() => lineArray.remove(index)}
                          >
                            Remove
                          </button>
                        )}
                      </span>
                    </div>
                  )
                })}
              </div>
              {booking && (
                <div className="available-expenses">
                  <span className="meta-label">Approved expenses available</span>
                  {booking.additional_expenses
                    .filter(
                      (item) =>
                        item.authorization_status === 'approved' &&
                        !lines.some((line) => line.source_expense_id === item.id),
                    )
                    .map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className="text-button"
                        onClick={() =>
                          lineArray.append({
                            description: item.description,
                            quantity: item.quantity,
                            unit: item.unit,
                            unit_rate: item.unit_rate,
                            category: 'expense',
                            source_booking_line_item_id: null,
                            source_expense_id: item.id!,
                          })
                        }
                      >
                        + Add {item.description} · {money(item.amount_cents)}
                      </button>
                    ))}
                </div>
              )}
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>Tax treatment</h2>
                <span className="muted">
                  Select the agreed treatment; no tax advice is provided.
                </span>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="tax_mode">Tax treatment</label>
                  <select id="tax_mode" {...form.register('tax_mode')}>
                    <option value="none">Tax not applied</option>
                    <option value="rate">Apply specified rate</option>
                    <option value="manual">Enter manually confirmed amount</option>
                  </select>
                </div>
                {taxMode === 'rate' && (
                  <div className="field">
                    <label htmlFor="tax_rate">Tax rate (%)</label>
                    <input id="tax_rate" inputMode="decimal" {...form.register('tax_rate')} />
                    <small className="muted">Confirm the applicable treatment independently.</small>
                  </div>
                )}
                {taxMode === 'manual' && (
                  <div className="field">
                    <label htmlFor="manual_tax">Tax amount ($)</label>
                    <input id="manual_tax" inputMode="decimal" {...form.register('manual_tax')} />
                  </div>
                )}
                <div className="field field--wide">
                  <label htmlFor="invoice-notes">Invoice notes</label>
                  <textarea id="invoice-notes" {...form.register('notes')} />
                </div>
              </div>
              <div className="invoice-totals">
                <div>
                  <span>Subtotal</span>
                  <strong>{money(subtotalCents)}</strong>
                </div>
                <div>
                  <span>Tax</span>
                  <strong>{money(calculatedTax)}</strong>
                </div>
                <div className="invoice-grand">
                  <span>Total</span>
                  <strong>{money(subtotalCents + calculatedTax)}</strong>
                </div>
              </div>
            </Panel>
            <div className="save-bar">
              <span className="muted">
                A draft invoice is independent from the accepted booking. Issue locks its snapshot.
              </span>
              <button className="button button--primary" disabled={save.isPending || !booking}>
                {save.isPending ? 'Saving…' : invoice ? 'Save invoice draft' : 'Save invoice draft'}
              </button>
            </div>
          </fieldset>
        </form>
        {invoice && (
          <Panel>
            <div className="section-heading">
              <h2>Review and issue</h2>
              {invoice.issued_at && (
                <span className="muted">Issued {dateLabel(invoice.issued_at)}</span>
              )}
            </div>
            <div className="action-row">
              <PdfPreview request={{ document_type: 'invoice', entity_id: invoice.id }} />
              {invoice.record_status === 'draft' && (
                <button
                  className="button button--primary"
                  disabled={issue.isPending}
                  onClick={() => issue.mutate()}
                >
                  {issue.isPending ? 'Issuing…' : 'Issue invoice and save PDF'}
                </button>
              )}
              {invoice.record_status === 'issued' && (
                <button
                  className="button"
                  disabled={generated.isPending}
                  onClick={() => generated.mutate()}
                >
                  {generated.isPending ? 'Generating…' : 'Save another PDF version'}
                </button>
              )}
            </div>
            <p className="muted">
              Save changes before previewing; preview uses the latest saved draft. Final PDFs are
              versioned and never overwritten.
            </p>
            {lastGeneratedName && <p role="status">{lastGeneratedName}</p>}
            {invoice.record_status === 'issued' && invoice.is_current && (
              <div className="payment-panel">
                <h3>Record a payment</h3>
                <p>
                  Balance due: <strong>{money(invoice.balance_due_cents)}</strong>
                </p>
                {invoice.balance_due_cents > 0 && (
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="payment-date">Payment date</label>
                      <input
                        id="payment-date"
                        type="date"
                        value={paymentDate}
                        onChange={(event) => setPaymentDate(event.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="payment-amount">Amount ($)</label>
                      <input
                        id="payment-amount"
                        inputMode="decimal"
                        value={paymentAmount}
                        onChange={(event) => setPaymentAmount(event.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="payment-method">Method</label>
                      <input
                        id="payment-method"
                        value={paymentMethod}
                        onChange={(event) => setPaymentMethod(event.target.value)}
                        placeholder="Check, ACH, etc."
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="payment-reference">Reference</label>
                      <input
                        id="payment-reference"
                        value={paymentReference}
                        onChange={(event) => setPaymentReference(event.target.value)}
                      />
                    </div>
                    <div className="field field--wide">
                      <label htmlFor="payment-notes">Notes</label>
                      <textarea
                        id="payment-notes"
                        value={paymentNotes}
                        onChange={(event) => setPaymentNotes(event.target.value)}
                      />
                    </div>
                    <div className="field field--wide">
                      <button
                        className="button"
                        disabled={payment.isPending || !paymentAmount.trim()}
                        onClick={() => payment.mutate()}
                      >
                        {payment.isPending ? 'Saving…' : 'Record payment'}
                      </button>
                    </div>
                  </div>
                )}
                {invoice.payments.map((item) => (
                  <p key={item.id}>
                    {dateLabel(item.paid_at)} · {money(item.amount_cents)} ·{' '}
                    {item.method || 'Payment'}
                  </p>
                ))}
                {invoice.is_current && invoice.amount_paid_cents === 0 && (
                  <button
                    className="button button--quiet"
                    disabled={revision.isPending}
                    onClick={() => revision.mutate()}
                  >
                    {revision.isPending ? 'Preparing…' : 'Create replacement revision'}
                  </button>
                )}
              </div>
            )}
          </Panel>
        )}
      </div>
    </>
  )
}
