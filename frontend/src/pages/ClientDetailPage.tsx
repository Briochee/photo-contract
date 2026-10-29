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
  const [signedDate, setSignedDate] = useState(todayIso())
  const [acceptanceReference, setAcceptanceReference] = useState('')
  const [signedCopy, setSignedCopy] = useState<File | null>(null)
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
  const selectAgreement = (selectedId: number) => {
    setSignedDate(todayIso())
    setAcceptanceReference('')
    setSignedCopy(null)
    setAgreementId(selectedId)
  }

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
    mutationFn: () => api.createAgreement({ client_id: clientId }),
    onSuccess: async (agreement) => {
      selectAgreement(agreement.id)
      await refresh()
    },
  })
  const finalizeAgreement = useMutation({
    mutationFn: (evidenceReference: string) =>
      api.finalizeAgreement(agreementId!, {
        signed_date: signedDate,
        evidence_reference: evidenceReference,
      }),
    onSuccess: refresh,
  })
  const uploadSignedCopy = useMutation({
    mutationFn: (file: File) => api.uploadSignedAgreement(agreementId!, signedDate, file),
    onSuccess: async () => {
      setSignedCopy(null)
      await Promise.all([
        refresh(),
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
    },
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
      await Promise.all([
        refresh(),
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
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
            finalizeAgreement.error ||
            uploadSignedCopy.error ||
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
            <div>
              <h2>Contracts</h2>
              <span className="muted">Draft → pending signature → finalized</span>
            </div>
            <button
              className="button"
              type="button"
              disabled={createAgreement.isPending}
              onClick={() => createAgreement.mutate()}
            >
              {createAgreement.isPending ? 'Creating…' : 'Create contract'}
            </button>
          </div>
          {!record.agreements.length ? (
            <p className="muted">No contract yet. Create one from this client’s saved details.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Last signature</th>
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
                        {agreement.status === 'finalized'
                          ? dateLabel(agreement.effective_date)
                          : '—'}
                      </td>
                      <td>
                        <Status
                          value={
                            agreement.status === 'pending' ? 'Pending signature' : agreement.status
                          }
                        />
                      </td>
                      <td>{agreement.template_version}</td>
                      <td>
                        <div className="table-actions">
                          <button
                            className="text-button"
                            type="button"
                            onClick={() => selectAgreement(agreement.id)}
                          >
                            Select
                          </button>
                          <button
                            className="text-button text-button--danger"
                            type="button"
                            disabled={
                              deleteAgreement.isPending ||
                              record.bookings.some(
                                (booking) => booking.agreement_id === agreement.id,
                              )
                            }
                            title={
                              record.bookings.some(
                                (booking) => booking.agreement_id === agreement.id,
                              )
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
                trailingAction={
                  selectedAgreement.status !== 'finalized' && (
                    <button
                      className="button button--primary"
                      onClick={() => generate.mutate()}
                      disabled={generate.isPending}
                    >
                      {generate.isPending
                        ? 'Saving…'
                        : selectedAgreement.status === 'draft'
                          ? 'Save PDF and mark pending'
                          : 'Save another PDF version'}
                    </button>
                  )
                }
              />
            ) : (
              <p className="muted">Select a contract to preview or save its PDF.</p>
            )}
            {selectedAgreement?.status === 'pending' && (
              <div className="agreement-finalization">
                <h3>Finalize contract</h3>
                <div className="agreement-finalize-grid">
                  <div className="field">
                    <label htmlFor="last-signature-date">Date of last signature</label>
                    <input
                      id="last-signature-date"
                      type="date"
                      value={signedDate}
                      onChange={(event) => setSignedDate(event.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="signed-copy">Upload signed PDF</label>
                    <input
                      id="signed-copy"
                      type="file"
                      accept="application/pdf,.pdf"
                      onChange={(event) => setSignedCopy(event.target.files?.[0] ?? null)}
                    />
                    <small className="field-hint">PDF only, up to 25 MB.</small>
                  </div>
                  <button
                    className="button button--primary"
                    type="button"
                    disabled={!signedCopy || uploadSignedCopy.isPending}
                    onClick={() => signedCopy && uploadSignedCopy.mutate(signedCopy)}
                  >
                    {uploadSignedCopy.isPending ? 'Uploading…' : 'Upload signed copy & finalize'}
                  </button>
                </div>
                <div className="agreement-reference-row">
                  <div className="field">
                    <label htmlFor="acceptance-ref">Or record an acceptance reference</label>
                    <input
                      id="acceptance-ref"
                      value={acceptanceReference}
                      onChange={(event) => setAcceptanceReference(event.target.value)}
                      placeholder="Email thread or signed-copy location"
                    />
                  </div>
                  <button
                    className="button"
                    type="button"
                    disabled={!acceptanceReference.trim() || finalizeAgreement.isPending}
                    onClick={() => finalizeAgreement.mutate(acceptanceReference.trim())}
                  >
                    {finalizeAgreement.isPending ? 'Finalizing…' : 'Finalize with reference'}
                  </button>
                  <button
                    className="button button--quiet"
                    type="button"
                    disabled={finalizeAgreement.isPending}
                    onClick={() => {
                      const confirmed = window.confirm(
                        'This records that you have confirmed the agreement outside Contract Studio. The app does not verify the signatures. Finalize this contract as confirmed?',
                      )
                      if (confirmed) finalizeAgreement.mutate('confirmed')
                    }}
                  >
                    Finalize as confirmed
                  </button>
                </div>
                <p className="muted agreement-help">
                  The uploaded PDF is stored in Documents. Contract Studio records your evidence but
                  does not validate PDF signatures or verify signer identity.
                </p>
              </div>
            )}
            {selectedAgreement?.status === 'finalized' && (
              <div className="inline-note agreement-help">
                Finalized on {dateLabel(selectedAgreement.effective_date)}. Evidence:{' '}
                {selectedAgreement.acceptance_reference || 'Confirmed'}.
                {selectedAgreement.acceptance_reference.startsWith('Uploaded signed PDF:') && (
                  <>
                    {' '}
                    The signed copy is in <Link to="/documents">Documents</Link>.
                  </>
                )}
              </div>
            )}
            {selectedAgreement && generate.data?.reference === selectedAgreement.agreement_ref && (
              <p className="agreement-help" role="status">
                Saved {generate.data.name} in the document library.
              </p>
            )}
          </div>
          <p className="inline-note">
            Create a contract as Draft. Saving its PDF moves it to Pending signature. Upload the
            signed copy, record an acceptance reference, or explicitly confirm it to finalize.
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
                            disabled={
                              !['draft', 'pending'].includes(booking.status) ||
                              deleteBooking.isPending
                            }
                            title={
                              ['draft', 'pending'].includes(booking.status)
                                ? 'Delete this unaccepted booking and any unpaid draft invoices.'
                                : 'Finalized and cancelled bookings are retained for the record.'
                            }
                            aria-label={`Delete booking ${booking.booking_ref}`}
                            onClick={() => {
                              const confirmed = window.confirm(
                                `Delete unaccepted booking ${booking.booking_ref}? Any unpaid draft invoices will also be deleted. Saved PDFs remain in Documents without a booking link. Finalized bookings and bookings with issued invoices or payments cannot be deleted.`,
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
