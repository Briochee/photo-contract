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
import { bookingSchema } from '../schemas'
import type { Booking, BookingPayload, ExpenseInput } from '../types'
import { dateLabel, money, todayIso } from '../utils/format'
import { lineAmountCents } from '../utils/money'

type FormInput = z.input<typeof bookingSchema>
type Values = z.output<typeof bookingSchema>
const packageDescription =
  'Corporate event photography package (up to six hours; editing and delivery included)'

function emptyValues(clientId = 0, rate = '800.00', overtime = '150.00'): Values {
  return {
    client_id: clientId,
    agreement_id: null,
    event_name: '',
    event_type: '',
    event_date: todayIso(),
    venue: '',
    venue_address: '',
    coverage_start: '09:00',
    coverage_end: '15:00',
    coverage_hours: '6',
    scope: '',
    delivery_method: 'Online gallery',
    delivery_deadline: '',
    special_deliverables: '',
    guaranteed_image_count: null,
    overtime_rate: overtime,
    payment_terms_days: 15,
    exceptions: '',
    line_items: [
      {
        description: packageDescription,
        quantity: '1',
        unit: 'package',
        unit_rate: rate,
        category: 'photography',
      },
    ],
    additional_expenses: [],
  }
}

export function BookingEditorPage() {
  const idText = useParams().bookingId
  const bookingId = idText ? Number(idText) : null
  const [params] = useSearchParams()
  const clientIdFromUrl = Number(params.get('client')) || 0
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const bookingQuery = useQuery({
    queryKey: ['booking', bookingId],
    queryFn: () => api.booking(bookingId!),
    enabled: Boolean(bookingId),
  })
  const clients = useQuery({ queryKey: ['clients', 'all'], queryFn: () => api.clients() })
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const agreements = useQuery({ queryKey: ['agreements'], queryFn: api.agreements })
  const form = useForm<FormInput, unknown, Values>({
    resolver: zodResolver(bookingSchema),
    defaultValues: emptyValues(clientIdFromUrl),
  })
  const lineArray = useFieldArray({ control: form.control, name: 'line_items' })
  const expenseArray = useFieldArray({ control: form.control, name: 'additional_expenses' })
  const watchedLines = useWatch({ control: form.control, name: 'line_items' }) ?? []
  const watchedExpenses = useWatch({ control: form.control, name: 'additional_expenses' }) ?? []
  const selectedClientId = useWatch({ control: form.control, name: 'client_id' })
  const [acceptedDate, setAcceptedDate] = useState(todayIso())
  const [acceptanceReference, setAcceptanceReference] = useState('')
  const [newExpense, setNewExpense] = useState<ExpenseInput>({
    description: '',
    quantity: '1',
    unit: 'service',
    unit_rate: '0.00',
    category: 'expense',
    authorization_status: 'proposed',
    authorization_date: null,
    authorization_reference: '',
    notes: '',
  })
  const [amendField, setAmendField] = useState('event_date')
  const [amendValue, setAmendValue] = useState('')
  const [amendSummary, setAmendSummary] = useState('')
  const [amendDate, setAmendDate] = useState(todayIso())
  const [amendReference, setAmendReference] = useState('')

  useEffect(() => {
    const booking = bookingQuery.data
    if (booking) {
      form.reset({
        client_id: booking.client_id,
        agreement_id: booking.agreement_id,
        event_name: booking.event_name,
        event_type: booking.event_type,
        event_date: booking.event_date,
        venue: booking.venue,
        venue_address: booking.venue_address,
        coverage_start: booking.coverage_start,
        coverage_end: booking.coverage_end,
        coverage_hours: booking.coverage_hours,
        scope: booking.scope,
        delivery_method: booking.delivery_method,
        delivery_deadline: booking.delivery_deadline,
        special_deliverables: booking.special_deliverables,
        guaranteed_image_count: booking.guaranteed_image_count,
        overtime_rate: booking.overtime_rate,
        payment_terms_days: booking.payment_terms_days,
        exceptions: booking.exceptions,
        line_items: booking.line_items.map(
          ({ description, quantity, unit, unit_rate, category }) => ({
            description,
            quantity,
            unit,
            unit_rate,
            category: category ?? 'service',
          }),
        ),
        additional_expenses: booking.additional_expenses.map(
          ({
            description,
            quantity,
            unit,
            unit_rate,
            category,
            authorization_status,
            authorization_date,
            authorization_reference,
            notes,
          }) => ({
            description,
            quantity,
            unit,
            unit_rate,
            category: category ?? 'expense',
            authorization_status:
              authorization_status === 'approved' || authorization_status === 'rejected'
                ? authorization_status
                : 'proposed',
            authorization_date: authorization_date ?? null,
            authorization_reference: authorization_reference ?? '',
            notes: notes ?? '',
          }),
        ),
      })
    } else if (!bookingId && settings.data) {
      form.reset(
        emptyValues(
          clientIdFromUrl,
          settings.data.profile.default_photography_rate ?? '800.00',
          settings.data.profile.default_overtime_rate ?? '150.00',
        ),
      )
    }
  }, [bookingId, bookingQuery.data, clientIdFromUrl, form, settings.data])

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['bookings'] })
    await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    if (bookingId) await queryClient.invalidateQueries({ queryKey: ['booking', bookingId] })
  }
  const save = useMutation({
    mutationFn: (value: BookingPayload) =>
      bookingId ? api.updateBooking(bookingId, value) : api.createBooking(value),
    onSuccess: async (value) => {
      await refresh()
      navigate(`/bookings/${value.id}`)
    },
  })
  const accept = useMutation({
    mutationFn: () =>
      api.acceptBooking(bookingId!, {
        accepted_date: acceptedDate,
        acceptance_reference: acceptanceReference,
      }),
    onSuccess: refresh,
  })
  const addExpense = useMutation({
    mutationFn: () => api.addExpense(bookingId!, newExpense),
    onSuccess: async () => {
      await refresh()
      setNewExpense({
        ...newExpense,
        description: '',
        authorization_reference: '',
        authorization_date: null,
      })
    },
  })
  const amend = useMutation({
    mutationFn: () =>
      api.amendments(bookingId!, {
        change_summary: amendSummary,
        changes: { [amendField]: amendValue },
        written_acceptance_date: amendDate,
        acceptance_reference: amendReference,
        accepted: true,
      }),
    onSuccess: async () => {
      await refresh()
      setAmendSummary('')
      setAmendReference('')
    },
  })
  const generate = useMutation({
    mutationFn: () =>
      api.generateDocument({ document_type: 'booking_confirmation', entity_id: bookingId! }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
      await refresh()
    },
  })

  if ((bookingId && bookingQuery.isLoading) || clients.isLoading || settings.isLoading)
    return <Loading />
  const booking = bookingQuery.data
  const locked = booking?.status === 'accepted'
  const baseCents = watchedLines.reduce(
    (sum, item) => sum + lineAmountCents(item?.quantity ?? '0', item?.unit_rate ?? '0'),
    0,
  )
  const approvedCents = watchedExpenses.reduce(
    (sum, item) =>
      sum +
      (item?.authorization_status === 'approved'
        ? lineAmountCents(item.quantity, item.unit_rate)
        : 0),
    0,
  )

  return (
    <>
      <PageHeader
        eyebrow="Booking / Assignment record"
        title={booking?.booking_ref ?? 'New booking'}
        description={
          booking
            ? `${booking.client.legal_name} · ${booking.event_name}`
            : 'Build a clear assignment brief and review the agreed fees.'
        }
        action={
          <Link className="button button--quiet" to="/bookings">
            ← Bookings
          </Link>
        }
      />
      <div className="stack">
        <ErrorMessage
          error={
            bookingQuery.error ||
            clients.error ||
            settings.error ||
            agreements.error ||
            save.error ||
            accept.error ||
            addExpense.error ||
            amend.error ||
            generate.error
          }
        />
        {booking && (
          <div className="record-banner">
            <div>
              <span className="eyebrow">Booking reference</span>
              <strong>{booking.booking_ref}</strong>
            </div>
            <Status value={booking.status} />
            <span className="muted">Created {dateLabel(booking.created_at)}</span>
          </div>
        )}
        <form
          className="stack"
          onSubmit={form.handleSubmit((value) => save.mutate(value as BookingPayload))}
        >
          <fieldset className="form-fieldset" disabled={Boolean(locked)}>
            <Panel shadow>
              <div className="section-heading">
                <h2>01 · Client and agreement</h2>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="client_id">Client *</label>
                  <select id="client_id" {...form.register('client_id', { valueAsNumber: true })}>
                    <option value={0}>Select a client</option>
                    {clients.data?.map((client) => (
                      <option key={client.id} value={client.id}>
                        {client.display_name || client.legal_name}
                      </option>
                    ))}
                  </select>
                  {form.formState.errors.client_id && (
                    <FieldError>{form.formState.errors.client_id.message}</FieldError>
                  )}
                </div>
                <div className="field">
                  <label htmlFor="agreement_id">Governing agreement</label>
                  <select
                    id="agreement_id"
                    {...form.register('agreement_id', {
                      setValueAs: (value) => (value === '' ? null : Number(value)),
                    })}
                  >
                    <option value="">Select agreement</option>
                    {agreements.data
                      ?.filter((agreement) => agreement.client_id === selectedClientId)
                      .map((agreement) => (
                        <option key={agreement.id} value={agreement.id}>
                          {agreement.agreement_ref} · {agreement.status}
                        </option>
                      ))}
                  </select>
                  <small className="muted">Create an agreement from the client record.</small>
                </div>
              </div>
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>02 · Event details</h2>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="event_name">Event / assignment *</label>
                  <input id="event_name" {...form.register('event_name')} />
                  {form.formState.errors.event_name && (
                    <FieldError>{form.formState.errors.event_name.message}</FieldError>
                  )}
                </div>
                <div className="field">
                  <label htmlFor="event_type">Event type</label>
                  <input id="event_type" {...form.register('event_type')} />
                </div>
                <div className="field">
                  <label htmlFor="event_date">Event date *</label>
                  <input id="event_date" type="date" {...form.register('event_date')} />
                </div>
                <div className="field">
                  <label htmlFor="venue">Venue</label>
                  <input id="venue" {...form.register('venue')} />
                </div>
                <div className="field field--wide">
                  <label htmlFor="venue_address">Venue address</label>
                  <textarea id="venue_address" {...form.register('venue_address')} />
                </div>
              </div>
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>03 · Coverage</h2>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="coverage_start">Coverage begins</label>
                  <input id="coverage_start" type="time" {...form.register('coverage_start')} />
                </div>
                <div className="field">
                  <label htmlFor="coverage_end">Coverage ends</label>
                  <input id="coverage_end" type="time" {...form.register('coverage_end')} />
                </div>
                <div className="field">
                  <label htmlFor="coverage_hours">Included coverage hours</label>
                  <input
                    id="coverage_hours"
                    inputMode="decimal"
                    {...form.register('coverage_hours')}
                  />
                  {form.formState.errors.coverage_hours && (
                    <FieldError>{form.formState.errors.coverage_hours.message}</FieldError>
                  )}
                </div>
                <div className="field">
                  <label htmlFor="overtime_rate">Overtime rate per hour ($)</label>
                  <input
                    id="overtime_rate"
                    inputMode="decimal"
                    {...form.register('overtime_rate')}
                  />
                </div>
              </div>
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>04 · Scope and deliverables</h2>
              </div>
              <div className="form-grid">
                <div className="field field--wide">
                  <label htmlFor="scope">Scope and priorities</label>
                  <textarea id="scope" {...form.register('scope')} />
                </div>
                <div className="field">
                  <label htmlFor="delivery_method">Delivery method</label>
                  <input id="delivery_method" {...form.register('delivery_method')} />
                </div>
                <div className="field">
                  <label htmlFor="delivery_deadline">Delivery deadline</label>
                  <input id="delivery_deadline" {...form.register('delivery_deadline')} />
                </div>
                <div className="field">
                  <label htmlFor="guaranteed_image_count">Guaranteed image count</label>
                  <input
                    id="guaranteed_image_count"
                    type="number"
                    min="0"
                    {...form.register('guaranteed_image_count', {
                      setValueAs: (value) => (value === '' ? null : Number(value)),
                    })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="special_deliverables">Special deliverables</label>
                  <textarea id="special_deliverables" {...form.register('special_deliverables')} />
                </div>
              </div>
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>05 · Agreed pricing</h2>
                <button
                  className="button button--quiet"
                  type="button"
                  onClick={() =>
                    lineArray.append({
                      description: '',
                      quantity: '1',
                      unit: 'service',
                      unit_rate: '0.00',
                      category: 'service',
                    })
                  }
                >
                  Add line
                </button>
              </div>
              <p className="inline-note">
                These charges appear in both the accepted booking confirmation and invoice. Accepted
                pricing requires an agreed amendment to change.
              </p>
              <div className="line-list" role="group" aria-label="Agreed booking line items">
                <div className="line-row line-row--head">
                  <span>Item</span>
                  <span>Quantity</span>
                  <span>Unit</span>
                  <span className="numeric">Rate</span>
                  <span className="numeric">Amount</span>
                  <span>Order</span>
                </div>
                {lineArray.fields.map((field, index) => (
                  <div className="line-row" key={field.id}>
                    <div className="field">
                      <label className="sr-only" htmlFor={`line-description-${index}`}>
                        Line {index + 1} description
                      </label>
                      <input
                        id={`line-description-${index}`}
                        {...form.register(`line_items.${index}.description`)}
                        placeholder="Service description"
                      />
                      {form.formState.errors.line_items?.[index]?.description && (
                        <FieldError>
                          {form.formState.errors.line_items[index]?.description?.message}
                        </FieldError>
                      )}
                    </div>
                    <div className="field">
                      <label className="sr-only" htmlFor={`line-quantity-${index}`}>
                        Line {index + 1} quantity
                      </label>
                      <input
                        id={`line-quantity-${index}`}
                        inputMode="decimal"
                        {...form.register(`line_items.${index}.quantity`)}
                      />
                    </div>
                    <div className="field">
                      <label className="sr-only" htmlFor={`line-unit-${index}`}>
                        Line {index + 1} unit
                      </label>
                      <select
                        id={`line-unit-${index}`}
                        {...form.register(`line_items.${index}.unit`)}
                      >
                        <option value="package">package</option>
                        <option value="hour">hour</option>
                        <option value="day">day</option>
                        <option value="image">image</option>
                        <option value="service">service</option>
                      </select>
                    </div>
                    <div className="field">
                      <label className="sr-only" htmlFor={`line-rate-${index}`}>
                        Line {index + 1} rate
                      </label>
                      <input
                        id={`line-rate-${index}`}
                        inputMode="decimal"
                        {...form.register(`line_items.${index}.unit_rate`)}
                      />
                    </div>
                    <output className="line-amount">
                      {money(
                        lineAmountCents(
                          watchedLines[index]?.quantity ?? '0',
                          watchedLines[index]?.unit_rate ?? '0',
                        ),
                      )}
                    </output>
                    <div className="line-actions">
                      <button
                        type="button"
                        className="text-button"
                        disabled={index === 0}
                        onClick={() => lineArray.move(index, index - 1)}
                        aria-label={`Move line ${index + 1} up`}
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        className="text-button"
                        disabled={index === lineArray.fields.length - 1}
                        onClick={() => lineArray.move(index, index + 1)}
                        aria-label={`Move line ${index + 1} down`}
                      >
                        ↓
                      </button>
                      <button
                        type="button"
                        className="text-button text-button--danger"
                        onClick={() => lineArray.remove(index)}
                        aria-label={`Remove line ${index + 1}`}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              {form.formState.errors.line_items?.root && (
                <FieldError>{form.formState.errors.line_items.root.message}</FieldError>
              )}
              <div className="financial-summary">
                <span>Agreed booking fees</span>
                <strong>{money(baseCents)}</strong>
              </div>
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>06 · Additional expenses</h2>
                <button
                  className="button button--quiet"
                  type="button"
                  onClick={() =>
                    expenseArray.append({
                      description: '',
                      quantity: '1',
                      unit: 'service',
                      unit_rate: '0.00',
                      category: 'expense',
                      authorization_status: 'proposed',
                      authorization_date: null,
                      authorization_reference: '',
                      notes: '',
                    })
                  }
                >
                  Add expense
                </button>
              </div>
              <p className="muted">
                Only expenses with documented written authorization may be billed. Proposed charges
                stay out of invoice totals.
              </p>
              {expenseArray.fields.map((field, index) => (
                <div className="expense-row" key={field.id}>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor={`expense-desc-${index}`}>Description</label>
                      <input
                        id={`expense-desc-${index}`}
                        {...form.register(`additional_expenses.${index}.description`)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`expense-status-${index}`}>Authorization</label>
                      <select
                        id={`expense-status-${index}`}
                        {...form.register(`additional_expenses.${index}.authorization_status`)}
                      >
                        <option value="proposed">Proposed</option>
                        <option value="approved">Approved in writing</option>
                        <option value="rejected">Rejected</option>
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor={`expense-qty-${index}`}>Quantity</label>
                      <input
                        id={`expense-qty-${index}`}
                        {...form.register(`additional_expenses.${index}.quantity`)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`expense-rate-${index}`}>Rate ($)</label>
                      <input
                        id={`expense-rate-${index}`}
                        {...form.register(`additional_expenses.${index}.unit_rate`)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`expense-date-${index}`}>Approval date</label>
                      <input
                        id={`expense-date-${index}`}
                        type="date"
                        {...form.register(`additional_expenses.${index}.authorization_date`, {
                          setValueAs: (value) => value || null,
                        })}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`expense-reference-${index}`}>Approval reference</label>
                      <input
                        id={`expense-reference-${index}`}
                        {...form.register(`additional_expenses.${index}.authorization_reference`)}
                      />
                    </div>
                    <div className="field field--wide">
                      <label htmlFor={`expense-notes-${index}`}>Notes</label>
                      <textarea
                        id={`expense-notes-${index}`}
                        {...form.register(`additional_expenses.${index}.notes`)}
                      />
                    </div>
                  </div>
                  <div className="expense-footer">
                    <span>
                      {watchedExpenses[index]?.authorization_status === 'approved'
                        ? `Approved amount: ${money(lineAmountCents(watchedExpenses[index]?.quantity ?? '0', watchedExpenses[index]?.unit_rate ?? '0'))}`
                        : 'Not currently billable'}
                    </span>
                    <button
                      type="button"
                      className="text-button text-button--danger"
                      onClick={() => expenseArray.remove(index)}
                    >
                      Remove expense
                    </button>
                  </div>
                </div>
              ))}
              {approvedCents > 0 && (
                <div className="financial-summary">
                  <span>Approved expense amount · separate from agreed fees</span>
                  <strong>{money(approvedCents)}</strong>
                </div>
              )}
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>07 · Payment terms and exceptions</h2>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="payment_terms_days">Calendar days after invoice date</label>
                  <input
                    id="payment_terms_days"
                    type="number"
                    min="0"
                    max="365"
                    {...form.register('payment_terms_days')}
                  />
                </div>
                <div className="field">
                  <label htmlFor="exceptions">Exceptions to master agreement</label>
                  <textarea id="exceptions" {...form.register('exceptions')} />
                  <small className="muted">
                    Identify the affected section and replacement terms.
                  </small>
                </div>
              </div>
            </Panel>
            <div className="save-bar">
              <span className="muted">Totals are independently recalculated by the backend.</span>
              <button className="button button--primary" disabled={save.isPending}>
                {save.isPending ? 'Saving…' : booking ? 'Save draft changes' : 'Save booking draft'}
              </button>
            </div>
          </fieldset>
        </form>
        {booking && (
          <Panel>
            <div className="section-heading">
              <h2>08 · Review and documents</h2>
              <Status value={booking.status} />
            </div>
            {booking.status === 'draft' && (
              <div className="acceptance-controls">
                <p className="inline-note">
                  Record written acceptance evidence here. The application does not obtain or verify
                  client consent.
                </p>
                <div className="field">
                  <label htmlFor="accepted-date">Written acceptance date</label>
                  <input
                    id="accepted-date"
                    type="date"
                    value={acceptedDate}
                    onChange={(event) => setAcceptedDate(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="acceptance-reference">Acceptance evidence reference</label>
                  <input
                    id="acceptance-reference"
                    value={acceptanceReference}
                    onChange={(event) => setAcceptanceReference(event.target.value)}
                    placeholder="Signed copy or email reference"
                  />
                </div>
                <button
                  className="button"
                  disabled={accept.isPending || !acceptanceReference.trim()}
                  onClick={() => accept.mutate()}
                >
                  {accept.isPending ? 'Recording…' : 'Record written acceptance'}
                </button>
              </div>
            )}
            <div className="action-row">
              <PdfPreview
                request={{ document_type: 'booking_confirmation', entity_id: booking.id }}
              />
              <button
                className="button button--primary"
                disabled={generate.isPending}
                onClick={() => generate.mutate()}
              >
                {generate.isPending ? 'Generating…' : 'Save PDF version'}
              </button>
            </div>
            {generate.data && (
              <p role="status">
                Saved {generate.data.name}. <Link to="/documents">Open document library</Link>
              </p>
            )}
            {booking.invoices?.map((invoice) => (
              <p key={invoice.id}>
                <Link to={`/invoices/${invoice.id}`}>
                  Invoice {invoice.invoice_ref} · {invoice.status}
                </Link>
              </p>
            ))}
          </Panel>
        )}
        {locked && (
          <ExpensePanel
            bookingId={booking!.id}
            expenses={booking!.additional_expenses}
            dataChanged={refresh}
          />
        )}
        {locked && (
          <AmendmentPanel
            booking={booking!}
            mutation={amend}
            state={{
              amendField,
              setAmendField,
              amendValue,
              setAmendValue,
              amendSummary,
              setAmendSummary,
              amendDate,
              setAmendDate,
              amendReference,
              setAmendReference,
            }}
          />
        )}
      </div>
    </>
  )
}

function ExpensePanel({
  bookingId,
  expenses,
  dataChanged,
}: {
  bookingId: number
  expenses: Booking['additional_expenses']
  dataChanged: () => Promise<void>
}) {
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [rate, setRate] = useState('0.00')
  const [status, setStatus] = useState<'proposed' | 'approved'>('proposed')
  const [approvalDate, setApprovalDate] = useState('')
  const [approvalReference, setApprovalReference] = useState('')
  const addExpense = useMutation({
    mutationFn: () =>
      api.addExpense(bookingId, {
        description,
        quantity,
        unit: 'service',
        unit_rate: rate,
        category: 'expense',
        authorization_status: status,
        authorization_date: approvalDate || null,
        authorization_reference: approvalReference,
        notes: '',
      }),
    onSuccess: async () => {
      setDescription('')
      await dataChanged()
    },
  })
  return (
    <Panel>
      <div className="section-heading">
        <h2>Additional expenses after acceptance</h2>
      </div>
      <p className="muted">
        These remain separate from accepted base pricing. Only documented approvals can be invoiced.
      </p>
      <ErrorMessage error={addExpense.error} />
      <div className="form-grid">
        <div className="field">
          <label htmlFor="post-expense-description">Description</label>
          <input
            id="post-expense-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="post-expense-status">Authorization</label>
          <select
            id="post-expense-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as 'proposed' | 'approved')}
          >
            <option value="proposed">Proposed</option>
            <option value="approved">Approved in writing</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="post-expense-quantity">Quantity</label>
          <input
            id="post-expense-quantity"
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="post-expense-rate">Rate</label>
          <input
            id="post-expense-rate"
            value={rate}
            onChange={(event) => setRate(event.target.value)}
          />
        </div>
        {status === 'approved' && (
          <>
            <div className="field">
              <label htmlFor="post-expense-date">Written approval date</label>
              <input
                id="post-expense-date"
                type="date"
                value={approvalDate}
                onChange={(event) => setApprovalDate(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="post-expense-reference">Approval reference</label>
              <input
                id="post-expense-reference"
                value={approvalReference}
                onChange={(event) => setApprovalReference(event.target.value)}
              />
            </div>
          </>
        )}
      </div>
      <button
        className="button"
        disabled={
          addExpense.isPending ||
          !description.trim() ||
          (status === 'approved' && (!approvalDate || !approvalReference.trim()))
        }
        onClick={() => addExpense.mutate()}
      >
        Add expense
      </button>
      {expenses.map((expense) => (
        <p key={expense.id}>
          <strong>{expense.description}</strong> · {money(expense.amount_cents)} ·{' '}
          <Status value={expense.authorization_status ?? 'proposed'} />
        </p>
      ))}
    </Panel>
  )
}

function AmendmentPanel({
  booking,
  mutation,
  state,
}: {
  booking: Pick<Booking, 'amendments'>
  mutation: { isPending: boolean; mutate: () => void }
  state: {
    amendField: string
    setAmendField: (value: string) => void
    amendValue: string
    setAmendValue: (value: string) => void
    amendSummary: string
    setAmendSummary: (value: string) => void
    amendDate: string
    setAmendDate: (value: string) => void
    amendReference: string
    setAmendReference: (value: string) => void
  }
}) {
  return (
    <Panel>
      <div className="section-heading">
        <h2>Record an accepted amendment</h2>
      </div>
      <p className="inline-note">
        The original accepted snapshot and generated PDFs remain available. Apply only a change
        backed by written client acceptance.
      </p>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="amend-field">Amended field</label>
          <select
            id="amend-field"
            value={state.amendField}
            onChange={(event) => state.setAmendField(event.target.value)}
          >
            <option value="event_date">Event date</option>
            <option value="event_name">Event name</option>
            <option value="scope">Scope and priorities</option>
            <option value="delivery_deadline">Delivery deadline</option>
            <option value="overtime_rate">Overtime rate</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="amend-value">New value</label>
          <input
            id="amend-value"
            type={state.amendField === 'event_date' ? 'date' : 'text'}
            value={state.amendValue}
            onChange={(event) => state.setAmendValue(event.target.value)}
          />
        </div>
        <div className="field field--wide">
          <label htmlFor="amend-summary">Change summary</label>
          <textarea
            id="amend-summary"
            value={state.amendSummary}
            onChange={(event) => state.setAmendSummary(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="amend-date">Written acceptance date</label>
          <input
            id="amend-date"
            type="date"
            value={state.amendDate}
            onChange={(event) => state.setAmendDate(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="amend-reference">Acceptance evidence reference</label>
          <input
            id="amend-reference"
            value={state.amendReference}
            onChange={(event) => state.setAmendReference(event.target.value)}
          />
        </div>
      </div>
      <button
        className="button"
        disabled={
          mutation.isPending ||
          !state.amendValue.trim() ||
          !state.amendSummary.trim() ||
          !state.amendReference.trim()
        }
        onClick={() => mutation.mutate()}
      >
        Record amendment
      </button>
      {booking.amendments.map((amendment) => (
        <p key={amendment.id}>
          <strong>{amendment.reference}</strong> · {amendment.change_summary} · {amendment.status}
        </p>
      ))}
    </Panel>
  )
}
