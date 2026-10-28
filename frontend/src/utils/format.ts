export function money(cents: number): string {
  const sign = cents < 0 ? '-' : ''
  const whole = Math.floor(Math.abs(cents) / 100)
  const fraction = String(Math.abs(cents) % 100).padStart(2, '0')
  return `${sign}$${new Intl.NumberFormat('en-US').format(whole)}.${fraction}`
}

export function dateLabel(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(`${value.slice(0, 10)}T12:00:00`)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

export function todayIso(): string {
  const now = new Date()
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}
