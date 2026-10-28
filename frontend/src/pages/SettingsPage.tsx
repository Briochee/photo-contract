import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { ErrorMessage, FieldError, Loading, PageHeader, Panel } from '../components/common/Ui'
import { api } from '../services/api'
import { profileSchema } from '../schemas'
import type { Profile } from '../types'

type Values = z.infer<typeof profileSchema>
type FormInput = z.input<typeof profileSchema>

export function SettingsPage() {
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const form = useForm<FormInput, unknown, Values>({ resolver: zodResolver(profileSchema) })
  useEffect(() => {
    if (settings.data) form.reset(settings.data.profile)
  }, [settings.data, form])
  const update = useMutation({
    mutationFn: (profile: Profile) => api.updateSettings(profile),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
  if (settings.isLoading) return <Loading />
  return (
    <>
      <PageHeader
        eyebrow="Studio / Local configuration"
        title="Settings"
        description="Defaults apply to new records. Existing agreements, bookings, and invoices keep their saved snapshots."
      />
      <div className="stack">
        <ErrorMessage error={settings.error || update.error} />
        <Panel shadow>
          <div className="section-heading">
            <h2>Photographer profile</h2>
            <span className="eyebrow">Used in future documents</span>
          </div>
          <form className="form-grid" onSubmit={form.handleSubmit((value) => update.mutate(value))}>
            <div className="field">
              <label htmlFor="legal_name">Photographer legal name</label>
              <input id="legal_name" {...form.register('legal_name')} />
            </div>
            <div className="field">
              <label htmlFor="business_name">Business name</label>
              <input id="business_name" {...form.register('business_name')} />
            </div>
            <div className="field field--wide">
              <label htmlFor="mailing_address">Mailing address</label>
              <textarea id="mailing_address" {...form.register('mailing_address')} />
            </div>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input id="email" type="email" {...form.register('email')} />
              {form.formState.errors.email && (
                <FieldError>{form.formState.errors.email.message}</FieldError>
              )}
            </div>
            <div className="field">
              <label htmlFor="phone">Phone</label>
              <input id="phone" type="tel" {...form.register('phone')} />
            </div>
            <div className="field field--wide">
              <label htmlFor="payment_instructions">Payment instructions</label>
              <textarea id="payment_instructions" {...form.register('payment_instructions')} />
            </div>
            <div className="field">
              <label htmlFor="default_photography_rate">Default photography rate ($)</label>
              <input id="default_photography_rate" {...form.register('default_photography_rate')} />
            </div>
            <div className="field">
              <label htmlFor="default_overtime_rate">Default overtime rate ($)</label>
              <input id="default_overtime_rate" {...form.register('default_overtime_rate')} />
            </div>
            <div className="field">
              <label htmlFor="default_payment_terms_days">
                Default payment terms (calendar days)
              </label>
              <input
                id="default_payment_terms_days"
                type="number"
                min="0"
                max="365"
                {...form.register('default_payment_terms_days')}
              />
            </div>
            <div className="field">
              <label htmlFor="default_delivery_method">Default delivery method</label>
              <input id="default_delivery_method" {...form.register('default_delivery_method')} />
            </div>
            <div className="field field--wide">
              <label htmlFor="default_delivery_deadline">Default delivery deadline</label>
              <input
                id="default_delivery_deadline"
                {...form.register('default_delivery_deadline')}
              />
            </div>
            <div className="field field--wide">
              <button className="button button--primary" disabled={update.isPending}>
                {update.isPending ? 'Saving…' : 'Save settings'}
              </button>
            </div>
          </form>
        </Panel>
        <Panel>
          <div className="section-heading">
            <h2>Local storage</h2>
            <span className="eyebrow">No cloud sync</span>
          </div>
          <dl className="settings-list">
            <div>
              <dt>Database and records</dt>
              <dd>
                <code>{settings.data?.output_directory.replace(/\/documents$/, '')}</code>
              </dd>
            </div>
            <div>
              <dt>Generated PDFs</dt>
              <dd>
                <code>{settings.data?.output_directory}</code>
              </dd>
            </div>
            <div>
              <dt>PDF page size</dt>
              <dd>{settings.data?.preferences.pdf_page_size} · US Letter</dd>
            </div>
          </dl>
          <p className="inline-note">
            Back up this local data directory before moving the studio to another computer. Review
            client information before sharing any archive.
          </p>
        </Panel>
        <Panel>
          <div className="section-heading">
            <h2>Backup and restore</h2>
            <span className="eyebrow">Local archive</span>
          </div>
          <p>
            A backup includes a transaction-consistent SQLite copy, local settings, legacy records,
            and generated PDFs.
          </p>
          <a className="button" href="/api/settings/backup">
            Download data backup
          </a>
          <p className="muted">
            Restore into a new or empty directory with{' '}
            <code>python scripts/restore_backup.py backup.zip /path/to/restored-data</code>, then
            set <code>PHOTO_STUDIO_DATA_DIR</code> to that directory.
          </p>
        </Panel>
      </div>
    </>
  )
}
