import { describe, expect, it } from 'vitest'
import { profileSchema } from './schemas'

const emptyOptionalProfile = {
  legal_name: 'Riley Photographer',
  business_name: '',
  mailing_address: '',
  email: '',
  phone: '',
  payment_instructions: '',
  default_payment_terms_days: '',
  currency: 'USD' as const,
  default_photography_rate: '',
  default_overtime_rate: '',
  default_delivery_method: '',
  default_delivery_deadline: '',
}

describe('photographer profile form', () => {
  it('accepts a profile without a company name or optional defaults', () => {
    const profile = profileSchema.parse(emptyOptionalProfile)

    expect(profile.business_name).toBeNull()
    expect(profile.default_payment_terms_days).toBeNull()
    expect(profile.default_photography_rate).toBeNull()
    expect(profile.default_overtime_rate).toBeNull()
    expect(profile.default_delivery_method).toBeNull()
    expect(profile.default_delivery_deadline).toBeNull()
  })

  it('keeps configured default values', () => {
    const profile = profileSchema.parse({
      ...emptyOptionalProfile,
      business_name: 'Northlight Studio',
      default_payment_terms_days: 15,
      default_photography_rate: '800.00',
      default_overtime_rate: '150.00',
      default_delivery_method: 'Online gallery',
      default_delivery_deadline: 'Within ten business days',
    })

    expect(profile.business_name).toBe('Northlight Studio')
    expect(profile.default_payment_terms_days).toBe(15)
    expect(profile.default_photography_rate).toBe('800.00')
    expect(profile.default_overtime_rate).toBe('150.00')
  })
})
