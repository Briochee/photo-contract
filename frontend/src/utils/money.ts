function toScaled(value: string, places: number): bigint | null {
  const match = /^(\d+)(?:\.(\d{0,3}))?$/.exec(value.trim())
  if (!match) return null
  const whole = BigInt(match[1] ?? '0')
  const fraction = BigInt((match[2] ?? '').padEnd(places, '0').slice(0, places) || '0')
  return whole * 10n ** BigInt(places) + fraction
}

export function decimalToCents(value: string): number {
  const milli = toScaled(value, 3)
  return milli === null ? 0 : Number((milli + 5n) / 10n)
}

export function lineAmountCents(quantity: string, rate: string): number {
  const quantityMilli = toScaled(quantity, 3)
  const rateMilli = toScaled(rate, 3)
  if (quantityMilli === null || rateMilli === null) return 0
  const rateCents = (rateMilli + 5n) / 10n
  return Number((quantityMilli * rateCents + 500n) / 1000n)
}

export function calculateTaxCents(
  subtotalCents: number,
  mode: 'none' | 'rate' | 'manual',
  rate: string,
  manual: string,
): number {
  if (mode === 'none') return 0
  if (mode === 'manual') return decimalToCents(manual)
  const rateMilli = toScaled(rate, 3)
  if (rateMilli === null) return 0
  return Number((BigInt(subtotalCents) * rateMilli + 50_000n) / 100_000n)
}
