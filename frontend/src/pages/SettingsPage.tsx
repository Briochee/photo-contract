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

function profileFormValues(profile: Profile): FormInput {
  return {
    ...profile,
    business_name: profile.business_name ?? '',
    default_payment_terms_days: profile.default_payment_terms_days ?? '',
    default_photography_rate: profile.default_photography_rate ?? '',
    default_overtime_rate: profile.default_overtime_rate ?? '',
    default_delivery_method: profile.default_delivery_method ?? '',
    default_delivery_deadline: profile.default_delivery_deadline ?? '',
  }
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const form = useForm<FormInput, unknown, Values>({ resolver: zodResolver(profileSchema) })
  useEffect(() => {
    if (settings.data) form.reset(profileFormValues(settings.data.profile))
  }, [settings.data, form])
  const update = useMutation({
    mutationFn: (profile: Profile) => api.updateSettings(profile),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
  const clearData = useMutation({
    mutationFn: api.clearAllData,
    onSuccess: async () => {
      await queryClient.invalidateQueries()
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
        <ErrorMessage error={settings.error || update.error || clearData.error} />
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
              <label htmlFor="business_name">Business name (optional)</label>
              <input id="business_name" {...form.register('business_name')} />
              <span className="field-hint">
                Leave blank if you do not use a separate business name.
              </span>
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
              <label htmlFor="default_photography_rate">
                Default photography rate ($, optional)
              </label>
              <input
                id="default_photography_rate"
                type="number"
                min="0"
                step="0.01"
                {...form.register('default_photography_rate')}
              />
              {form.formState.errors.default_photography_rate && (
                <FieldError>{form.formState.errors.default_photography_rate.message}</FieldError>
              )}
            </div>
            <div className="field">
              <label htmlFor="default_overtime_rate">Default overtime rate ($, optional)</label>
              <input
                id="default_overtime_rate"
                type="number"
                min="0"
                step="0.01"
                {...form.register('default_overtime_rate')}
              />
              {form.formState.errors.default_overtime_rate && (
                <FieldError>{form.formState.errors.default_overtime_rate.message}</FieldError>
              )}
            </div>
            <div className="field">
              <label htmlFor="default_payment_terms_days">
                Default payment terms (calendar days, optional)
              </label>
              <input
                id="default_payment_terms_days"
                type="number"
                min="0"
                max="365"
                {...form.register('default_payment_terms_days', {
                  setValueAs: (value: string) => (value === '' ? '' : Number(value)),
                })}
              />
              {form.formState.errors.default_payment_terms_days && (
                <FieldError>{form.formState.errors.default_payment_terms_days.message}</FieldError>
              )}
            </div>
            <div className="field">
              <label htmlFor="default_delivery_method">Default delivery method (optional)</label>
              <input id="default_delivery_method" {...form.register('default_delivery_method')} />
            </div>
            <div className="field field--wide">
              <label htmlFor="default_delivery_deadline">
                Default delivery deadline (optional)
              </label>
              <input
                id="default_delivery_deadline"
                {...form.register('default_delivery_deadline')}
              />
            </div>
            <div className="field field--wide">
              <button
                className="button button--primary"
                disabled={update.isPending || clearData.isPending}
              >
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
        <Panel className="danger-panel">
          <div className="section-heading">
            <h2>Clear all history and data</h2>
            <span className="eyebrow">Permanent action</span>
          </div>
          <p>
            Remove all clients, contracts, bookings, invoices, payments, saved PDFs, photographer
            profile details, application preferences, and imported legacy records. Existing
            activity logs are cleared. Reference counters remain so previously used references are
            never reused. This only affects the configured Contract Studio data folder; backups
            and original source files stored elsewhere remain untouched.
          </p>
          <button
            className="button button--danger"
            type="button"
            disabled={clearData.isPending || update.isPending}
            onClick={() => {
              const confirmed = window.confirm(
                'This is irreversible.\n\nThis permanently removes all clients, contracts, bookings, invoices, payments, saved PDFs, your photographer profile, application preferences, imported legacy records, and existing activity logs from the configured Contract Studio data folder. Reference counters stay in place so previously used references are never reused. Download a backup first. Backups and original source files stored elsewhere are not affected.\n\nClear all history and data now?',
              )
              if (confirmed) clearData.mutate()
            }}
          >
            {clearData.isPending ? 'Clearing local data…' : 'Clear all history and data'}
          </button>
          {clearData.data && (
            <p
              className={
                clearData.data.local_files_cleared &&
                clearData.data.database_compacted &&
                clearData.data.logs_cleared
                  ? 'inline-note'
                  : 'error-box'
              }
              role={
                clearData.data.local_files_cleared &&
                clearData.data.database_compacted &&
                clearData.data.logs_cleared
                  ? 'status'
                  : 'alert'
              }
            >
              {clearData.data.local_files_cleared &&
              clearData.data.database_compacted &&
              clearData.data.logs_cleared
                ? 'Local records, documents, settings, and activity logs have been cleared. Reference counters were retained.'
                : 'Records were cleared, but some local files, database space, or logs could not be fully removed. Close other Contract Studio windows and retry the reset.'}
            </p>
          )}
        </Panel>
      </div>
    </>
  )
}
