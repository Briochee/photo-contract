import { z } from 'zod'

const decimalString = (label: string, allowZero = true) =>
  z
    .string()
    .trim()
    .regex(/^\d+(?:\.\d{1,3})?$/, `${label} must be a decimal number`)
    .refine((value) => allowZero || Number(value) > 0, `${label} must be greater than zero`)

const optionalDecimalString = (label: string) =>
  z
    .string()
    .trim()
    .max(32)
    .refine(
      (value) => !value || /^\d+(?:\.\d{1,3})?$/.test(value),
      `${label} must be a decimal number`,
    )
    .transform((value) => value || null)

const optionalText = (maxLength: number) =>
  z
    .string()
    .trim()
    .max(maxLength)
    .transform((value) => value || null)

export const clientSchema = z.object({
  legal_name: z.string().trim().min(1, 'Legal entity name is required').max(200),
  display_name: z.string().max(200).nullable().optional(),
  mailing_address: z.string().max(4000).default(''),
  primary_contact_name: z.string().max(160).default(''),
  primary_contact_title: z.string().max(160).default(''),
  contact_email: z.string().trim().email('Enter a valid email').or(z.literal('')).default(''),
  contact_phone: z.string().max(80).default(''),
  notes: z.string().max(10000).default(''),
})

export const lineItemSchema = z.object({
  description: z.string().trim().min(1, 'Description is required').max(300),
  quantity: decimalString('Quantity', false),
  unit: z.string().max(40).default('service'),
  unit_rate: decimalString('Rate'),
  category: z.string().max(80).default('service'),
})

export const bookingSchema = z.object({
  client_id: z.coerce.number().int().positive('Select a client'),
  agreement_id: z.number().int().positive().nullable(),
  event_name: z.string().trim().min(1, 'Assignment name is required').max(200),
  event_type: z.string().max(120).default(''),
  event_date: z.string().date('Enter an event date'),
  venue: z.string().max(200).default(''),
  venue_address: z.string().max(4000).default(''),
  coverage_start: z.string().min(1),
  coverage_end: z.string().min(1),
  coverage_hours: decimalString('Coverage hours', false),
  scope: z.string().max(10000).default(''),
  delivery_method: z.string().max(100).default('Online gallery'),
  delivery_deadline: z.string().max(120).default(''),
  special_deliverables: z.string().max(5000).default(''),
  guaranteed_image_count: z.coerce.number().int().nonnegative().nullable(),
  overtime_rate: decimalString('Overtime rate'),
  payment_terms_days: z.coerce.number().int().min(0).max(365),
  exceptions: z.string().max(5000).default(''),
  line_items: z.array(lineItemSchema).min(1, 'Add at least one agreed charge').max(100),
  additional_expenses: z
    .array(
      lineItemSchema.extend({
        authorization_status: z.enum(['proposed', 'approved', 'rejected']),
        authorization_date: z.string().nullable(),
        authorization_reference: z.string().max(200),
        notes: z.string().max(2000),
      }),
    )
    .max(100),
})

export const invoiceSchema = z.object({
  booking_id: z.coerce.number().int().positive(),
  invoice_date: z.string().date('Enter an invoice date'),
  due_date: z.string().date('Enter a due date'),
  tax_mode: z.enum(['none', 'rate', 'manual']),
  tax_rate: z.string(),
  manual_tax: z.string(),
  notes: z.string().max(5000),
  line_items: z.array(
    lineItemSchema.extend({
      source_booking_line_item_id: z.number().int().positive().nullable(),
      source_expense_id: z.number().int().positive().nullable(),
    }),
  ),
})

export const profileSchema = z.object({
  legal_name: z.string().max(200),
  business_name: optionalText(200),
  mailing_address: z.string().max(4000),
  email: z.string().trim().email('Enter a valid email').or(z.literal('')),
  phone: z.string().max(80),
  payment_instructions: z.string().max(4000),
  default_payment_terms_days: z
    .union([z.literal(''), z.number().int().min(0).max(365)])
    .transform((value) => (value === '' ? null : value)),
  currency: z.literal('USD'),
  default_photography_rate: optionalDecimalString('Photography rate'),
  default_overtime_rate: optionalDecimalString('Overtime rate'),
  default_delivery_method: optionalText(80),
  default_delivery_deadline: optionalText(120),
})
