import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorMessage } from './Ui'

type Props = {
  entityType: 'agreement' | 'booking' | 'invoice'
  entityId: number
}

export function RelatedDocumentUpload({ entityType, entityId }: Props) {
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const upload = useMutation({
    mutationFn: (selected: File) => api.attachDocument(entityType, entityId, selected),
    onSuccess: async () => {
      setFile(null)
      if (fileInput.current) fileInput.current.value = ''
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
    },
  })
  const inputId = `related-document-${entityType}-${entityId}`

  return (
    <section className="related-document-upload" aria-labelledby={`${inputId}-heading`}>
      <h3 id={`${inputId}-heading`}>Attach a related document</h3>
      <p className="muted">
        PDF, JPG, or PNG up to 25 MB. The file is added to Documents without reopening the record or
        changing its accepted terms or invoice amounts.
      </p>
      <ErrorMessage error={upload.error} />
      <form
        className="document-upload-form"
        onSubmit={(event) => {
          event.preventDefault()
          if (file) upload.mutate(file)
        }}
      >
        <div className="field">
          <label htmlFor={inputId}>Choose a related file</label>
          <input
            ref={fileInput}
            id={inputId}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            disabled={upload.isPending}
            onChange={(event) => setFile(event.currentTarget.files?.[0] ?? null)}
          />
        </div>
        <button className="button" type="submit" disabled={!file || upload.isPending}>
          {upload.isPending ? 'Attaching…' : 'Attach file'}
        </button>
      </form>
      {upload.data && (
        <p className="field-hint" role="status">
          Attached {upload.data.name}. <Link to="/documents">View in Documents</Link>.
        </p>
      )}
    </section>
  )
}
