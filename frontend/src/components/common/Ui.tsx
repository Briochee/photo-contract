import type { PropsWithChildren, ReactNode } from 'react'

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <header className="page-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </header>
  )
}

export function Panel({
  children,
  shadow = false,
  className = '',
}: PropsWithChildren<{ shadow?: boolean; className?: string }>) {
  return (
    <section className={`panel ${shadow ? 'panel--shadow' : ''} ${className}`.trim()}>
      {children}
    </section>
  )
}

export function Status({ value }: { value: string }) {
  const normalized = value.toLowerCase().replaceAll(' ', '_')
  return <span className={`status status--${normalized}`}>{value.replaceAll('_', ' ')}</span>
}

export function ErrorMessage({ error }: { error: unknown }) {
  if (!error) return null
  return (
    <div className="error-box" role="alert">
      {error instanceof Error ? error.message : 'Something went wrong. Please try again.'}
    </div>
  )
}

export function Loading({ label = 'Loading local records…' }: { label?: string }) {
  return (
    <p className="loading" role="status">
      {label}
    </p>
  )
}

export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string
  detail: string
  action?: ReactNode
}) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{detail}</p>
      {action}
    </div>
  )
}

export function FieldError({ children }: PropsWithChildren) {
  if (!children) return null
  return (
    <span className="field-error" role="alert">
      {children}
    </span>
  )
}
