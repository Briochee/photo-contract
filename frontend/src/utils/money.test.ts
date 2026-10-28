import { describe, expect, it } from 'vitest'
import { calculateTaxCents, decimalToCents, lineAmountCents } from './money'

describe('money preview calculations', () => {
  it('rounds monetary values to cents using half-up rounding', () => {
    expect(decimalToCents('12.345')).toBe(1235)
  })

  it('supports fractional quantities without binary floating-point math', () => {
    expect(lineAmountCents('1.5', '0.10')).toBe(15)
    expect(lineAmountCents('2.125', '10.00')).toBe(2125)
  })

  it('calculates percentage and manual tax in minor units', () => {
    expect(calculateTaxCents(101, 'rate', '8.5', '0')).toBe(9)
    expect(calculateTaxCents(0, 'manual', '0', '0.105')).toBe(11)
    expect(calculateTaxCents(10_000, 'none', '8.5', '50')).toBe(0)
  })
})
