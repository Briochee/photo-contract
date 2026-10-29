import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
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
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const uploadDocument = useMutation({
    mutationFn: api.uploadDocument,
    onSuccess: async () => {
      setSelectedFile(null)
      if (fileInput.current) fileInput.current.value = ''
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
    },
  })
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
        eyebrow="Library / Local documents"
        title="Documents"
        description="Generated business PDFs and uploaded reference files, stored on this device."
      />
      <Panel shadow>
        <div className="section-heading">
          <h2>Upload a reference file</h2>
        </div>
        <ErrorMessage error={uploadDocument.error} />
        <form
          className="document-upload-form"
          onSubmit={(event) => {
            event.preventDefault()
            if (selectedFile) uploadDocument.mutate(selectedFile)
          }}
        >
          <div className="field">
            <label htmlFor="reference-file">Choose a file</label>
            <input
              ref={fileInput}
              id="reference-file"
              name="reference-file"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              onChange={(event) => setSelectedFile(event.currentTarget.files?.[0] ?? null)}
              aria-describedby="reference-file-hint"
            />
          </div>
          <button
            className="button button--primary"
            type="submit"
            disabled={!selectedFile || uploadDocument.isPending}
          >
            {uploadDocument.isPending ? 'Saving file…' : 'Add to document library'}
          </button>
        </form>
        <p id="reference-file-hint" className="field-hint document-upload-hint">
          PDF, JPG, or PNG up to 25 MB. Files stay in this device’s local library and are not
          attached to a client, booking, or invoice.
          {selectedFile && <strong> Selected: {selectedFile.name}</strong>}
        </p>
      </Panel>
      <Panel>
        <ErrorMessage error={documents.error || removeDocument.error} />
        <p className="muted">
          Draft PDFs are working copies. Agreement PDFs awaiting signatures show as pending. Final
          PDFs are accepted or issued versions. Deleting a PDF here does not change its source
          record.
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
              <option value="uploaded_file">Uploaded files</option>
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
                  <th>Added</th>
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
                      {document.client_id && document.client_name ? (
                        <Link to={`/clients/${document.client_id}`}>{document.client_name}</Link>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      {document.document_type === 'uploaded_file'
                        ? '—'
                        : document.invoice_reference ||
                          document.booking_reference ||
                          document.reference}
                    </td>
                    <td>
                      {document.document_type === 'uploaded_file' ? '—' : `v${document.version}`}
                    </td>
                    <td>{dateLabel(document.created_at)}</td>
                    <td>
                      <Status
                        value={
                          document.document_type === 'uploaded_file'
                            ? 'Stored locally'
                            : document.status === 'pending'
                              ? 'Pending signature'
                              : document.status === 'final'
                                ? 'Final PDF'
                                : 'Draft PDF'
                        }
                      />
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
                            document.document_type === 'uploaded_file'
                              ? `Permanently delete ${document.name} from the local document library?`
                              : `Permanently delete ${document.name} and remove it from the document library? The related ${document.document_type.replaceAll('_', ' ')} record will remain.`,
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
            title="No documents"
            detail="Save a PDF from an agreement, booking, or invoice, or upload a local reference file."
          />
        )}
      </Panel>
      {previewId && (
        <Panel shadow>
          <div className="section-heading">
            <h2>Saved document preview</h2>
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
            This is the stored file. Generated PDFs remain unchanged when current client or booking
            data changes.
          </p>
        </Panel>
      )}
    </>
  )
}
