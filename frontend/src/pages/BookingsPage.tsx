import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
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

export function BookingsPage() {
  const queryClient = useQueryClient()
  const bookings = useQuery({ queryKey: ['bookings'], queryFn: api.bookings })
  const deleteBooking = useMutation({
    mutationFn: api.deleteBooking,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['bookings'] }),
        queryClient.invalidateQueries({ queryKey: ['booking'] }),
        queryClient.invalidateQueries({ queryKey: ['client'] }),
        queryClient.invalidateQueries({ queryKey: ['clients'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['invoices'] }),
      ])
    },
  })
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')
  const filtered = useMemo(
    () =>
      bookings.data?.filter((booking) => {
        const matchesStatus = status === 'all' || booking.status === status
        const query = search.trim().toLowerCase()
        const matchesSearch =
          !query ||
          `${booking.booking_ref} ${booking.event_name} ${booking.client.legal_name}`
            .toLowerCase()
            .includes(query)
        return matchesStatus && matchesSearch
      }) ?? [],
    [bookings.data, search, status],
  )

  return (
    <>
      <PageHeader
        eyebrow="Bookings / Schedule and scope"
        title="Bookings"
        description="Manage bookings for weddings, portraits, celebrations, events, and other photography work."
        action={
          <Link to="/bookings/new" className="button button--primary">
            New booking
          </Link>
        }
      />
      <Panel>
        <ErrorMessage error={bookings.error || deleteBooking.error} />
        <div className="filter-row">
          <div className="field">
            <label htmlFor="booking-search">Search bookings</label>
            <input
              id="booking-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Reference, event, or client"
            />
          </div>
          <div className="field">
            <label htmlFor="booking-status">Status</label>
            <select
              id="booking-status"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="draft">Draft</option>
              <option value="pending">Pending</option>
              <option value="finalized">Finalized</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
        {bookings.isLoading ? (
          <Loading />
        ) : filtered.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Session / event</th>
                  <th>Client</th>
                  <th>Event date</th>
                  <th>Status</th>
                  <th className="numeric">Agreed fees</th>
                  <th className="actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((booking) => (
                  <tr key={booking.id}>
                    <td>{booking.booking_ref}</td>
                    <td>
                      <Link className="table-link" to={`/bookings/${booking.id}`}>
                        {booking.event_name}
                      </Link>
                    </td>
                    <td>{booking.client.display_name || booking.client.legal_name}</td>
                    <td>{dateLabel(booking.event_date)}</td>
                    <td>
                      <Status value={booking.status} />
                    </td>
                    <td className="numeric">{money(booking.subtotal_cents)}</td>
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
          <EmptyState
            title="No matching bookings"
            detail="Create a booking for any photography session or event and associate it with a client."
            action={
              <Link className="button" to="/bookings/new">
                New booking
              </Link>
            }
          />
        )}
      </Panel>
    </>
  )
}
