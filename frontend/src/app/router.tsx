import { lazy, Suspense, type ComponentType } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../components/layout/AppLayout'
import { Loading } from '../components/common/Ui'

const DashboardPage = lazy(() =>
  import('../pages/DashboardPage').then((page) => ({ default: page.DashboardPage })),
)
const ClientsPage = lazy(() =>
  import('../pages/ClientsPage').then((page) => ({ default: page.ClientsPage })),
)
const ClientDetailPage = lazy(() =>
  import('../pages/ClientDetailPage').then((page) => ({ default: page.ClientDetailPage })),
)
const BookingsPage = lazy(() =>
  import('../pages/BookingsPage').then((page) => ({ default: page.BookingsPage })),
)
const BookingEditorPage = lazy(() =>
  import('../pages/BookingEditorPage').then((page) => ({ default: page.BookingEditorPage })),
)
const InvoicesPage = lazy(() =>
  import('../pages/InvoicesPage').then((page) => ({ default: page.InvoicesPage })),
)
const InvoiceEditorPage = lazy(() =>
  import('../pages/InvoiceEditorPage').then((page) => ({ default: page.InvoiceEditorPage })),
)
const DocumentsPage = lazy(() =>
  import('../pages/DocumentsPage').then((page) => ({ default: page.DocumentsPage })),
)
const SettingsPage = lazy(() =>
  import('../pages/SettingsPage').then((page) => ({ default: page.SettingsPage })),
)

function page(Component: ComponentType) {
  return (
    <Suspense fallback={<Loading />}>
      <Component />
    </Suspense>
  )
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: page(DashboardPage) },
      { path: 'clients', element: page(ClientsPage) },
      { path: 'clients/:clientId', element: page(ClientDetailPage) },
      { path: 'bookings', element: page(BookingsPage) },
      { path: 'bookings/new', element: page(BookingEditorPage) },
      { path: 'bookings/:bookingId', element: page(BookingEditorPage) },
      { path: 'invoices', element: page(InvoicesPage) },
      { path: 'invoices/new', element: page(InvoiceEditorPage) },
      { path: 'invoices/:invoiceId', element: page(InvoiceEditorPage) },
      { path: 'documents', element: page(DocumentsPage) },
      { path: 'settings', element: page(SettingsPage) },
    ],
  },
])
