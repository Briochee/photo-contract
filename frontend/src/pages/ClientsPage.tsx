import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { ErrorMessage, FieldError, Loading, PageHeader, Panel } from '../components/common/Ui'
import { api } from '../services/api'
import { clientSchema } from '../schemas'

type ClientValues = z.infer<typeof clientSchema>
type ClientFormInput = z.input<typeof clientSchema>
const emptyClient: ClientValues = {
  legal_name: '',
  display_name: '',
  mailing_address: '',
  primary_contact_name: '',
  primary_contact_title: '',
  contact_email: '',
  contact_phone: '',
  notes: '',
}

export function ClientsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState(false)
  const clients = useQuery({ queryKey: ['clients', search], queryFn: () => api.clients(search) })
  const form = useForm<ClientFormInput, unknown, ClientValues>({
    resolver: zodResolver(clientSchema),
    defaultValues: emptyClient,
  })
  const create = useMutation({
    mutationFn: api.createClient,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      form.reset(emptyClient)
      setExpanded(false)
    },
  })

  return (
    <>
      <PageHeader
        eyebrow="Relationships / Local records"
        title="Clients"
        description="Keep legal entity details, contacts, agreements, bookings, and invoices together."
        action={
          <button className="button button--primary" onClick={() => setExpanded(!expanded)}>
            {expanded ? 'Close form' : 'New client'}
          </button>
        }
      />
      <div className="stack">
        <ErrorMessage error={clients.error || create.error} />
        {expanded && (
          <Panel shadow>
            <div className="section-heading">
              <h2>New client record</h2>
              <span className="eyebrow">Client details</span>
            </div>
            <form
              className="form-grid"
              onSubmit={form.handleSubmit((values) => create.mutate(values))}
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
                <label htmlFor="contact_email">Contact email</label>
                <input id="contact_email" type="email" {...form.register('contact_email')} />
                {form.formState.errors.contact_email && (
                  <FieldError>{form.formState.errors.contact_email.message}</FieldError>
                )}
              </div>
              <div className="field">
                <label htmlFor="contact_phone">Contact phone</label>
                <input id="contact_phone" type="tel" {...form.register('contact_phone')} />
              </div>
              <div className="field field--wide">
                <label htmlFor="notes">Internal notes</label>
                <textarea id="notes" {...form.register('notes')} />
              </div>
              <div className="field field--wide action-row">
                <button className="button button--primary" disabled={create.isPending}>
                  {create.isPending ? 'Saving…' : 'Save client'}
                </button>
              </div>
            </form>
          </Panel>
        )}
        <Panel>
          <div className="section-heading">
            <h2>Client directory</h2>
            <span className="muted">{clients.data?.length ?? 0} records</span>
          </div>
          <div className="search-row">
            <label className="meta-label" htmlFor="client-search">
              Find client
            </label>
            <input
              id="client-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search legal entity name"
            />
          </div>
          {clients.isLoading ? (
            <Loading />
          ) : clients.data?.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Client</th>
                    <th>Primary contact</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {clients.data.map((client) => (
                    <tr key={client.id}>
                      <td>
                        <Link className="table-link" to={`/clients/${client.id}`}>
                          {client.display_name || client.legal_name}
                        </Link>
                        <small className="table-subline">{client.legal_name}</small>
                      </td>
                      <td>{client.primary_contact_name || '—'}</td>
                      <td>{client.contact_email || '—'}</td>
                      <td>{client.contact_phone || '—'}</td>
                      <td>
                        <Link to={`/clients/${client.id}`} aria-label={`Open ${client.legal_name}`}>
                          Open →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <strong>No client records yet</strong>
              <p>Create a client before drafting a booking.</p>
              <button className="button" onClick={() => setExpanded(true)}>
                Create first client
              </button>
            </div>
          )}
        </Panel>
      </div>
    </>
  )
}
