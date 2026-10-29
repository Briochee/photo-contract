import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ErrorMessage,
  EmptyState,
  Loading,
  PageHeader,
  Panel,
  Status,
} from '../components/common/Ui'
import { api } from '../services/api'
import { dateLabel } from '../utils/format'

export function DocumentsPage() {
  const queryClient = useQueryClient()
  const documents = useQuery({ queryKey: ['documents'], queryFn: api.documents })
  const [previewId, setPreviewId] = useState<number | null>(null)
  const [kind, setKind] = useState('all')
  const removeDocument = useMutation({
    mutationFn: api.deleteDocument,
    onSuccess: async (_, deletedId) => {
      if (previewId === deletedId) setPreviewId(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
    },
  })
  const rows =
    documents.data?.filter((document) => kind === 'all' || document.document_type === kind) ?? []
  return (
    <>
      <PageHeader
        eyebrow="Library / Generated PDFs"
        title="Documents"
        description="Versioned agreements, booking confirmations, and invoices stored on this device."
      />
      <Panel>
        <ErrorMessage error={documents.error || removeDocument.error} />
        <p className="muted">
          Draft PDFs are working copies. Final PDFs were saved after written acceptance was recorded
          or an invoice was issued. Deleting a PDF here does not change its source record.
        </p>
        <div className="filter-row filter-row--single">
          <div className="field">
            <label htmlFor="document-type">Document type</label>
            <select
              id="document-type"
              value={kind}
              onChange={(event) => setKind(event.target.value)}
            >
              <option value="all">All documents</option>
              <option value="agreement">Master agreements</option>
              <option value="booking_confirmation">Booking confirmations</option>
              <option value="invoice">Invoices</option>
            </select>
          </div>
        </div>
        {documents.isLoading ? (
          <Loading />
        ) : rows.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Client</th>
                  <th>Related reference</th>
                  <th>Version</th>
                  <th>Generated</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((document) => (
                  <tr key={document.id}>
                    <td>
                      <strong>{document.name}</strong>
                      <small className="table-subline">
                        {document.document_type.replaceAll('_', ' ')}
                      </small>
                    </td>
                    <td>
                      <Link to={`/clients/${document.client_id}`}>{document.client_name}</Link>
                    </td>
                    <td>
                      {document.invoice_reference ||
                        document.booking_reference ||
                        document.reference}
                    </td>
                    <td>v{document.version}</td>
                    <td>{dateLabel(document.created_at)}</td>
                    <td>
                      <Status value={document.status === 'final' ? 'Final PDF' : 'Draft PDF'} />
                    </td>
                    <td className="action-cell">
                      <button
                        className="text-button"
                        onClick={() => setPreviewId(previewId === document.id ? null : document.id)}
                      >
                        {previewId === document.id ? 'Close preview' : 'Preview'}
                      </button>
                      <a className="text-button" href={api.downloadUrl(document.id)}>
                        Download
                      </a>
                      <button
                        className="text-button text-button--danger"
                        type="button"
                        disabled={removeDocument.isPending}
                        aria-label={`Delete ${document.name}`}
                        onClick={() => {
                          const confirmed = window.confirm(
                            `Permanently delete ${document.name} and remove it from the document library? The related ${document.document_type.replaceAll('_', ' ')} record will remain.`,
                          )
                          if (confirmed) removeDocument.mutate(document.id)
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No generated documents"
            detail="Save a draft or final PDF from an agreement, booking, or invoice record."
          />
        )}
      </Panel>
      {previewId && (
        <Panel shadow>
          <div className="section-heading">
            <h2>Saved PDF preview</h2>
            <button className="button button--quiet" onClick={() => setPreviewId(null)}>
              Close
            </button>
          </div>
          <iframe
            className="pdf-preview"
            title="Saved document PDF preview"
            src={api.documentPreviewUrl(previewId)}
          />
          <p className="muted">
            This is the stored historical PDF. It does not regenerate from current client or booking
            data.
          </p>
        </Panel>
      )}
    </>
  )
}
