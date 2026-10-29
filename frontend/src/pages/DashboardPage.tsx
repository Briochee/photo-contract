import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  EmptyState,
  ErrorMessage,
  Loading,
  PageHeader,
  Panel,
  Status,
} from '../components/common/Ui'
import { api } from '../services/api'
import { dateLabel, money } from '../utils/format'

export function DashboardPage() {
  const summary = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard })
  const data = summary.data

  return (
    <>
      <PageHeader
        eyebrow="Studio overview / Local records"
        title="Good work, in focus."
        description="Current bookings, invoices, and your next photography sessions and events."
        action={
          <Link className="button button--primary" to="/bookings/new">
            New booking
          </Link>
        }
      />
      <ErrorMessage error={summary.error} />
      {summary.isLoading && <Loading />}
      {data && (
        <div className="stack">
          <div className="metric-grid">
            <Metric
              label="Active bookings"
              value={String(data.active_bookings).padStart(2, '0')}
              note="Draft and accepted"
            />
            <Metric
              label="Upcoming bookings"
              value={String(data.upcoming_assignments.length).padStart(2, '0')}
              note="Scheduled from today"
            />
            <Metric
              label="Draft invoices"
              value={String(data.draft_invoices).padStart(2, '0')}
              note="Ready to review"
            />
            <Metric
              label="Outstanding balance"
              value={money(data.outstanding_balance_cents)}
              note={`${data.outstanding_invoices} open invoices`}
              accent
            />
          </div>
          <div className="dashboard-grid">
            <Panel shadow>
              <div className="section-heading">
                <h2>Upcoming bookings</h2>
                <Link to="/bookings">All bookings →</Link>
              </div>
              {data.upcoming_assignments.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Session / event</th>
                        <th>Client</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.upcoming_assignments.map((item) => (
                        <tr key={item.id}>
                          <td>{dateLabel(item.event_date)}</td>
                          <td>
                            <Link className="table-link" to={`/bookings/${item.id}`}>
                              {item.event_name}
                              <small className="table-subline">{item.booking_ref}</small>
                            </Link>
                          </td>
                          <td>{item.client_name}</td>
                          <td>
                            <Status value={item.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState
                  title="No upcoming bookings"
                  detail="Create a booking to keep your next work in view."
                />
              )}
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>Quick actions</h2>
              </div>
              <div className="quick-actions">
                <Link to="/clients" className="quick-action">
                  <span>01</span>
                  <strong>New client</strong>
                  <small>Save a client record</small>
                </Link>
                <Link to="/bookings/new" className="quick-action">
                  <span>02</span>
                  <strong>New booking</strong>
                  <small>Draft a confirmation</small>
                </Link>
                <Link to="/invoices/new" className="quick-action">
                  <span>03</span>
                  <strong>Create invoice</strong>
                  <small>Select any saved booking</small>
                </Link>
                <Link to="/documents" className="quick-action">
                  <span>04</span>
                  <strong>Document library</strong>
                  <small>Preview and download PDFs</small>
                </Link>
              </div>
            </Panel>
          </div>
          <div className="dashboard-grid dashboard-grid--lower">
            <Panel>
              <div className="section-heading">
                <h2>Recent clients</h2>
                <Link to="/clients">View clients →</Link>
              </div>
              {data.recent_clients.length ? (
                <ul className="plain-list">
                  {data.recent_clients.map((client) => (
                    <li key={client.id}>
                      <Link to={`/clients/${client.id}`}>
                        {client.display_name || client.legal_name}
                      </Link>
                      <span>{client.legal_name}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted">Client records will appear here.</p>
              )}
            </Panel>
            <Panel>
              <div className="section-heading">
                <h2>Recent documents</h2>
                <Link to="/documents">Library →</Link>
              </div>
              {data.recent_documents.length ? (
                <ul className="plain-list">
                  {data.recent_documents.map((document) => (
                    <li key={document.id}>
                      <Link to="/documents">
                        {document.reference} · {document.document_type.replaceAll('_', ' ')}
                      </Link>
                      <span>
                        <Status value={document.status} /> · {dateLabel(document.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted">Generated PDFs will appear here.</p>
              )}
            </Panel>
          </div>
        </div>
      )}
    </>
  )
}

function Metric({
  label,
  value,
  note,
  accent = false,
}: {
  label: string
  value: string
  note: string
  accent?: boolean
}) {
  return (
    <section className={`metric ${accent ? 'metric--accent' : ''}`}>
      <div className="meta-label">{label}</div>
      <strong>{value}</strong>
      <span>{note}</span>
    </section>
  )
}
