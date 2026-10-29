import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
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

export function InvoicesPage() {
  const invoices = useQuery({ queryKey: ['invoices'], queryFn: api.invoices })
  const [status, setStatus] = useState('all')
  const filtered = useMemo(
    () => invoices.data?.filter((invoice) => status === 'all' || invoice.status === status) ?? [],
    [invoices.data, status],
  )
  return (
    <>
      <PageHeader
        eyebrow="Accounts / Receivables"
        title="Invoices"
        description="Review drafts, record payments, and keep issued invoice versions unchanged."
      />
      <Panel>
        <ErrorMessage error={invoices.error} />
        <div className="filter-row filter-row--single">
          <div className="field">
            <label htmlFor="invoice-status">Status</label>
            <select
              id="invoice-status"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="draft">Draft</option>
              <option value="issued">Issued</option>
              <option value="partially_paid">Partially paid</option>
              <option value="overdue">Overdue</option>
              <option value="paid">Paid</option>
              <option value="voided">Replaced / voided</option>
            </select>
          </div>
        </div>
        {invoices.isLoading ? (
          <Loading />
        ) : filtered.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Client / session or event</th>
                  <th>Issued</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th className="numeric">Total</th>
                  <th className="numeric">Balance</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((invoice) => (
                  <tr key={invoice.id}>
                    <td>
                      {invoice.invoice_ref}
                      {invoice.version > 1 && (
                        <small className="table-subline">Revision {invoice.version}</small>
                      )}
                    </td>
                    <td>
                      <Link className="table-link" to={`/invoices/${invoice.id}`}>
                        {invoice.client.display_name || invoice.client.legal_name}
                      </Link>
                      <small className="table-subline">
                        {invoice.event_name} · {invoice.booking_ref}
                      </small>
                    </td>
                    <td>{dateLabel(invoice.invoice_date)}</td>
                    <td>{dateLabel(invoice.due_date)}</td>
                    <td>
                      <Status value={invoice.status} />
                    </td>
                    <td className="numeric">{money(invoice.total_cents)}</td>
                    <td className="numeric">{money(invoice.balance_due_cents)}</td>
                    <td>
                      <Link to={`/invoices/${invoice.id}`}>Open →</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No invoices in this view"
            detail="Create an invoice from an accepted booking."
            action={
              <Link className="button" to="/bookings">
                Open bookings
              </Link>
            }
          />
        )}
      </Panel>
    </>
  )
}
