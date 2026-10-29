import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../../services/api'
import type { DocumentRequest } from '../../types'
import { ErrorMessage } from './Ui'

type Props = {
  request: DocumentRequest | null
  leadingAction?: ReactNode
  trailingAction?: ReactNode
}

export function PdfPreview({ request, leadingAction, trailingAction }: Props) {
  const [url, setUrl] = useState<string | null>(null)
  const preview = useMutation({ mutationFn: api.previewDocument, onSuccess: setUrl })

  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url)
    },
    [url],
  )

  return (
    <div className="stack">
      <div className="action-row">
        {leadingAction}
        <button
          className="button button--quiet"
          type="button"
          disabled={!request || preview.isPending}
          onClick={() => request && preview.mutate(request)}
        >
          {preview.isPending ? 'Preparing preview…' : 'Preview PDF'}
        </button>
        {trailingAction}
        {url && (
          <a className="button button--quiet" href={url} target="_blank" rel="noreferrer">
            Open preview
          </a>
        )}
      </div>
      <ErrorMessage error={preview.error} />
      {url && <iframe className="pdf-preview" src={url} title="PDF document preview" />}
    </div>
  )
}
