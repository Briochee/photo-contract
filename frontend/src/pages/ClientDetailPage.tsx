import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useParams } from 'react-router-dom'
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
import { clientSchema } from '../schemas'
import { dateLabel, money, todayIso } from '../utils/format'

type Values = z.infer<typeof clientSchema>
type FormInput = z.input<typeof clientSchema>

export function ClientDetailPage() {
  const clientId = Number(useParams().clientId)
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [lastSignatureDate, setLastSignatureDate] = useState(todayIso())
  const [acceptanceReference, setAcceptanceReference] = useState('')
  const [agreementId, setAgreementId] = useState<number | null>(null)
  const client = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => api.client(clientId),
    enabled: Number.isFinite(clientId),
  })
  const form = useForm<FormInput, unknown, Values>({ resolver: zodResolver(clientSchema) })

  useEffect(() => {
    if (client.data) form.reset(client.data)
  }, [client.data, form])

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['client', clientId] })
    await queryClient.invalidateQueries({ queryKey: ['clients'] })
  }
  const update = useMutation({
    mutationFn: (value: Values) => api.updateClient(clientId, value),
    onSuccess: async () => {
      await refresh()
      setEditing(false)
    },
  })
  const createAgreement = useMutation({
    mutationFn: () =>
      api.createAgreement({ client_id: clientId, effective_date: todayIso(), accepted: false }),
    onSuccess: async (agreement) => {
      setAgreementId(agreement.id)
      await refresh()
    },
  })
  const acceptAgreement = useMutation({
    mutationFn: () =>
      api.acceptAgreement(agreementId!, {
        accepted_date: lastSignatureDate,
        acceptance_reference: acceptanceReference,
      }),
    onSuccess: refresh,
  })
  const deleteAgreement = useMutation({
    mutationFn: (id: number) => api.deleteAgreement(id),
    onSuccess: async (_, deletedId) => {
      if (agreementId === deletedId) setAgreementId(null)
      await refresh()
    },
  })
  const deleteBooking = useMutation({
    mutationFn: (id: number) => api.deleteBooking(id),
    onSuccess: async () => {
      await Promise.all([
        refresh(),
        queryClient.invalidateQueries({ queryKey: ['bookings'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['invoices'] }),
      ])
    },
  })
  const generate = useMutation({
    mutationFn: () => api.generateDocument({ document_type: 'agreement', entity_id: agreementId! }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
      await refresh()
    },
  })

  if (client.isLoading) return <Loading />
  if (!client.data)
    return (
      <>
        <PageHeader eyebrow="Client record" title="Client unavailable" />
        <ErrorMessage error={client.error ?? new Error('Client not found')} />
      </>
    )
  const record = client.data
  const selectedAgreement = record.agreements.find((item) => item.id === agreementId)
  return (
    <>
      <PageHeader
        eyebrow="Client record / Relationships"
        title={record.display_name || record.legal_name}
        description={record.legal_name}
        action={
          <Link className="button button--quiet" to="/clients">
            ← Client directory
          </Link>
        }
      />
      <div className="stack">
        <ErrorMessage
          error={
            update.error ||
            createAgreement.error ||
            acceptAgreement.error ||
            deleteAgreement.error ||
            deleteBooking.error ||
            generate.error
          }
        />
        <Panel shadow>
          <div className="section-heading">
            <h2>Contact details</h2>
            <button className="button button--quiet" onClick={() => setEditing(!editing)}>
              {editing ? 'Cancel editing' : 'Edit details'}
            </button>
          </div>
          {editing ? (
            <form
              className="form-grid"
              onSubmit={form.handleSubmit((value) => update.mutate(value))}
            >
              <div className="field">
                <label htmlFor="legal_name">Legal entity name *</label>
                <input id="legal_name" {...form.register('legal_name')} />
                {form.formState.errors.legal_name && (
                  <FieldError>{form.formState.errors.legal_name.message}</FieldError>
                )}
              </div>
              <div className="field">
                <label htmlFor="display_name">Display name</label>
                <input id="display_name" {...form.register('display_name')} />
              </div>
              <div className="field field--wide">
                <label htmlFor="mailing_address">Mailing address</label>
                <textarea id="mailing_address" {...form.register('mailing_address')} />
              </div>
              <div className="field">
                <label htmlFor="primary_contact_name">Primary contact</label>
                <input id="primary_contact_name" {...form.register('primary_contact_name')} />
              </div>
              <div className="field">
                <label htmlFor="primary_contact_title">Contact title</label>
                <input id="primary_contact_title" {...form.register('primary_contact_title')} />
              </div>
              <div className="field">
                <label htmlFor="contact_email">Email</label>
                <input type="email" id="contact_email" {...form.register('contact_email')} />
              </div>
              <div className="field">
                <label htmlFor="contact_phone">Phone</label>
                <input type="tel" id="contact_phone" {...form.register('contact_phone')} />
              </div>
              <div className="field field--wide">
                <label htmlFor="notes">Internal notes</label>
                <textarea id="notes" {...form.register('notes')} />
              </div>
              <div className="field field--wide">
                <button className="button button--primary" disabled={update.isPending}>
                  {update.isPending ? 'Saving…' : 'Save client details'}
                </button>
              </div>
            </form>
          ) : (
            <div className="detail-columns">
              <div>
                <span className="meta-label">Mailing address</span>
                <p className="preline">{record.mailing_address || 'Not recorded'}</p>
              </div>
              <div>
                <span className="meta-label">Primary contact</span>
                <p>
                  {record.primary_contact_name || 'Not recorded'}
                  {record.primary_contact_title ? ` · ${record.primary_contact_title}` : ''}
                  <br />
                  {record.contact_email || '—'}
                  <br />
                  {record.contact_phone || '—'}
                </p>
              </div>
              <div>
                <span className="meta-label">Internal notes</span>
                <p className="preline">{record.notes || 'No notes'}</p>
              </div>
            </div>
          )}
        </Panel>
        <Panel>
          <div className="section-heading">
            <h2>Contracts</h2>
            <span className="muted">Master agreements · controlled legal template</span>
          </div>
          {!record.agreements.length ? (
            <p className="muted">
              No agreement record yet. The legal text is kept as a controlled template.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Agreement date</th>
                    <th>Status</th>
                    <th>Template</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {record.agreements.map((agreement) => (
                    <tr key={agreement.id}>
                      <td>{agreement.agreement_ref}</td>
                      <td>
                        {agreement.status === 'accepted'
                          ? dateLabel(agreement.effective_date)
                          : 'Pending signature'}
                      </td>
                      <td>
                        <Status value={agreement.status} />
                      </td>
                      <td>{agreement.template_version}</td>
                      <td>
                        <div className="table-actions">
                          <button
                            className="text-button"
                            type="button"
                            onClick={() => setAgreementId(agreement.id)}
                          >
                            Select
                          </button>
                          <button
                            className="text-button text-button--danger"
                            type="button"
                            disabled={
                              deleteAgreement.isPending ||
                              record.bookings.some((booking) => booking.agreement_id === agreement.id)
                            }
                            title={
                              record.bookings.some((booking) => booking.agreement_id === agreement.id)
                                ? 'This agreement is linked to a booking.'
                                : undefined
                            }
                            aria-label={`Delete agreement ${agreement.agreement_ref}`}
                            onClick={() => {
                              const confirmed = window.confirm(
                                `Delete ${agreement.agreement_ref}? This removes the saved agreement and its acceptance record. Any generated PDF copies remain in Documents.`,
                              )
                              if (confirmed) deleteAgreement.mutate(agreement.id)
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="agreement-actions">
            {selectedAgreement ? (
              <PdfPreview
                key={selectedAgreement.id}
                request={{ document_type: 'agreement', entity_id: selectedAgreement.id }}
                leadingAction={
                  <button
                    className="button"
                    disabled={createAgreement.isPending}
                    onClick={() => createAgreement.mutate()}
                  >
                    Create draft agreement
                  </button>
                }
                trailingAction={
                  <button
                    className="button button--primary"
                    onClick={() => generate.mutate()}
                    disabled={generate.isPending}
                  >
                    {generate.isPending
                      ? 'Saving…'
                      : selectedAgreement.status === 'accepted'
                        ? 'Save final PDF version'
                        : 'Save draft PDF'}
                  </button>
                }
              />
            ) : (
              <div className="agreement-action-row">
                <button
                  className="button"
                  disabled={createAgreement.isPending}
                  onClick={() => createAgreement.mutate()}
                >
                  Create draft agreement
                </button>
              </div>
            )}
            {selectedAgreement?.status === 'draft' && (
              <>
                <div className="acceptance-fields">
                  <div className="field">
                    <label htmlFor="last-signature-date">Date of last signature</label>
                    <input
                      id="last-signature-date"
                      type="date"
                      value={lastSignatureDate}
                      onChange={(event) => setLastSignatureDate(event.target.value)}
                    />
                    <small className="field-hint">
                      This date becomes the agreement’s effective date.
                    </small>
                  </div>
                  <div className="field">
                    <label htmlFor="acceptance-ref">Signed agreement evidence</label>
                    <input
                      id="acceptance-ref"
                      value={acceptanceReference}
                      onChange={(event) => setAcceptanceReference(event.target.value)}
                      placeholder="Signed copy location or email record"
                    />
                    <small className="field-hint">
                      Record where the signed agreement is stored.
                    </small>
                  </div>
                  <button
                    className="button"
                    disabled={acceptAgreement.isPending || !acceptanceReference.trim()}
                    onClick={() => acceptAgreement.mutate()}
                  >
                    Record signed agreement
                  </button>
                </div>
                <p className="muted agreement-help">
                  A draft PDF is for review and can be prepared now. The agreement becomes accepted
                  only after you record the client’s written acceptance evidence.
                </p>
              </>
            )}
            {selectedAgreement?.status === 'accepted' && (
              <p className="inline-note agreement-help">
                Written acceptance is recorded. Generate a final PDF version below. You can prepare
                the booking confirmation and invoice before this step.
              </p>
            )}
            {generate.data && (
              <p className="agreement-help" role="status">
                Saved {generate.data.name} in the document library.
              </p>
            )}
          </div>
          <p className="inline-note">
            The PDF includes signer, date, and digital signature fields. Sign it in a compatible PDF
            app, save the signed copy, then record the last signature date and where that copy is
            stored. The app does not verify signer identity or automatically record acceptance.
          </p>
        </Panel>
        <Panel>
          <div className="section-heading">
            <h2>Bookings</h2>
            <Link className="button" to={`/bookings/new?client=${record.id}`}>
              New booking
            </Link>
          </div>
          {record.bookings.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Session / event</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th className="numeric">Chargeable total</th>
                    <th className="actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {record.bookings.map((booking) => (
                    <tr key={booking.id}>
                      <td>{booking.booking_ref}</td>
                      <td>
                        <Link className="table-link" to={`/bookings/${booking.id}`}>
                          {booking.event_name}
                        </Link>
                      </td>
                      <td>{dateLabel(booking.event_date)}</td>
                      <td>
                        <Status value={booking.status} />
                      </td>
                      <td className="numeric">{money(booking.total_chargeable_cents)}</td>
                      <td className="actions">
                        <div className="table-actions">
                          <Link className="text-button" to={`/bookings/${booking.id}`}>
                            Open
                          </Link>
                          <button
                            className="text-button text-button--danger"
                            type="button"
                            disabled={booking.status !== 'draft' || deleteBooking.isPending}
                            title={
                              booking.status === 'draft'
                                ? 'Delete this draft and any unpaid draft invoices.'
                                : 'Accepted and cancelled bookings are retained for the record.'
                            }
                            aria-label={`Delete booking ${booking.booking_ref}`}
                            onClick={() => {
                              const confirmed = window.confirm(
                                `Delete draft booking ${booking.booking_ref}? Any unpaid draft invoices will also be deleted. Saved PDFs remain in Documents without a booking link. Accepted bookings and bookings with issued invoices or payments cannot be deleted.`,
                              )
                              if (confirmed) deleteBooking.mutate(booking.id)
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">No bookings for this client.</p>
          )}
        </Panel>
        <Panel>
          <div className="section-heading">
            <h2>Invoices</h2>
          </div>
          {record.invoices.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Session / event</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th className="numeric">Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {record.invoices.map((invoice) => (
                    <tr key={invoice.id}>
                      <td>{invoice.invoice_ref}</td>
                      <td>
                        <Link className="table-link" to={`/invoices/${invoice.id}`}>
                          {invoice.event_name}
                        </Link>
                      </td>
                      <td>{dateLabel(invoice.invoice_date)}</td>
                      <td>
                        <Status value={invoice.status} />
                      </td>
                      <td className="numeric">{money(invoice.balance_due_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">No invoices for this client.</p>
          )}
        </Panel>
      </div>
    </>
  )
}
