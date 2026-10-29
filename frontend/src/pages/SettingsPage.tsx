import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
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
  const agreementTemplate = useQuery({
    queryKey: ['agreement-template'],
    queryFn: () => api.agreementTemplate(),
  })
  const form = useForm<FormInput, unknown, Values>({ resolver: zodResolver(profileSchema) })
  const [templateContent, setTemplateContent] = useState<string | null>(null)
  const [templateFileName, setTemplateFileName] = useState('')
  const [templateMessage, setTemplateMessage] = useState('')
  const editorContent = templateContent ?? agreementTemplate.data?.content ?? ''
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
  const saveAgreementTemplate = useMutation({
    mutationFn: () => api.saveAgreementTemplate(editorContent),
    onSuccess: async (saved) => {
      setTemplateContent(saved.content)
      setTemplateFileName('')
      setTemplateMessage(`Saved ${saved.template_version}. New agreements will use this version.`)
      await queryClient.invalidateQueries({ queryKey: ['agreement-template'] })
    },
  })
  const resetAgreementTemplate = useMutation({
    mutationFn: api.resetAgreementTemplate,
    onSuccess: async (restored) => {
      setTemplateContent(restored.content)
      setTemplateFileName('')
      setTemplateMessage('The built-in agreement is active again for new agreements.')
      await queryClient.invalidateQueries({ queryKey: ['agreement-template'] })
    },
  })

  const loadAgreementFile = async (file?: File) => {
    if (!file) return
    setTemplateMessage('')
    if (!/\.(md|markdown)$/i.test(file.name)) {
      setTemplateMessage('Choose a Markdown file ending in .md or .markdown.')
      return
    }
    if (file.size > 1_048_576) {
      setTemplateMessage('The agreement Markdown file must be 1 MB or smaller.')
      return
    }
    try {
      const content = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer())
      setTemplateContent(content)
      setTemplateFileName(file.name)
      setTemplateMessage(`${file.name} loaded. Save the template to activate it.`)
    } catch {
      setTemplateMessage('The selected Markdown file could not be read.')
    }
  }

  if (settings.isLoading) return <Loading />
  return (
    <>
      <PageHeader
        eyebrow="Studio / Local configuration"
        title="Settings"
        description="Defaults apply to new records. Existing agreements, bookings, and invoices keep their saved snapshots."
      />
      <div className="stack">
        <ErrorMessage
          error={
            settings.error ||
            agreementTemplate.error ||
            update.error ||
            saveAgreementTemplate.error ||
            resetAgreementTemplate.error ||
            clearData.error
          }
        />
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
            <h2>Master agreement template</h2>
            <span className="eyebrow">Local Markdown</span>
          </div>
          <p>
            Upload your own Markdown agreement or edit the active text here. Saving changes the
            template for new agreements immediately; existing agreements keep their saved text and
            PDFs. The template is stored with local application data, so no app rebuild is needed.
          </p>
          {agreementTemplate.data ? (
            <div className="record-banner agreement-template-status">
              <div>
                <span className="eyebrow">Active template</span>
                <strong>
                  {agreementTemplate.data.source === 'custom' ? 'Custom Markdown' : 'Built-in'}
                </strong>
              </div>
              <span className="muted">Version {agreementTemplate.data.template_version}</span>
              {agreementTemplate.data.updated_at && (
                <span className="muted">
                  Updated {new Date(agreementTemplate.data.updated_at).toLocaleString()}
                </span>
              )}
            </div>
          ) : agreementTemplate.isLoading ? (
            <p className="muted">Loading the active agreement template…</p>
          ) : null}
          <form
            className="stack agreement-template-form"
            onSubmit={(event) => {
              event.preventDefault()
              setTemplateMessage('')
              saveAgreementTemplate.mutate()
            }}
          >
            <div className="field">
              <label htmlFor="agreement-template-upload">Upload Markdown</label>
              <input
                id="agreement-template-upload"
                type="file"
                accept=".md,.markdown,text/markdown,text/plain"
                onChange={(event) => void loadAgreementFile(event.currentTarget.files?.[0])}
              />
              <span className="field-hint">
                Markdown only, up to 1 MB. Uploading fills the editor; press Save to activate it.
                {templateFileName ? ` Loaded file: ${templateFileName}.` : ''}
              </span>
            </div>
            <div className="field">
              <label htmlFor="agreement-template-content">Agreement Markdown</label>
              <textarea
                id="agreement-template-content"
                className="agreement-template-editor"
                rows={22}
                spellCheck={false}
                value={editorContent}
                onChange={(event) => setTemplateContent(event.currentTarget.value)}
                disabled={!agreementTemplate.data}
              />
              <span className="field-hint">
                Supported data tokens: <code>{'{{photographer_name}}'}</code>,{' '}
                <code>{'{{photographer_legal_name}}'}</code>,{' '}
                <code>{'{{photographer_business_name}}'}</code>,{' '}
                <code>{'{{photographer_address}}'}</code>, <code>{'{{photographer_email}}'}</code>,{' '}
                <code>{'{{photographer_phone}}'}</code>, <code>{'{{client_legal_name}}'}</code>,{' '}
                <code>{'{{client_display_name}}'}</code>, <code>{'{{client_address}}'}</code>,{' '}
                <code>{'{{client_contact_name}}'}</code>, <code>{'{{client_contact_title}}'}</code>,{' '}
                <code>{'{{client_email}}'}</code>, <code>{'{{client_phone}}'}</code>, and{' '}
                <code>{'{{agreement_effective_date}}'}</code>. Keep signature terms before a final
                Signatures heading; Contract Studio places its fillable photographer and client
                fields on that page. Raw HTML is escaped and Markdown images are omitted in PDFs;
                use text and tables rather than remote assets.
              </span>
            </div>
            <div className="action-row">
              <button
                className="button button--primary"
                disabled={
                  !agreementTemplate.data ||
                  !editorContent.trim() ||
                  saveAgreementTemplate.isPending ||
                  resetAgreementTemplate.isPending
                }
              >
                {saveAgreementTemplate.isPending ? 'Saving template…' : 'Save active agreement'}
              </button>
              <button
                className="button"
                type="button"
                disabled={
                  resetAgreementTemplate.isPending ||
                  saveAgreementTemplate.isPending ||
                  !agreementTemplate.data ||
                  (agreementTemplate.data.source === 'bundled' &&
                    editorContent === agreementTemplate.data.content)
                }
                onClick={() => {
                  if (agreementTemplate.data?.source === 'bundled') {
                    setTemplateContent(agreementTemplate.data.content)
                    setTemplateMessage('Unsaved edits were discarded.')
                  } else if (
                    window.confirm(
                      'Restore the built-in master agreement for future agreements? Existing agreements will keep their saved text.',
                    )
                  ) {
                    setTemplateMessage('')
                    resetAgreementTemplate.mutate()
                  }
                }}
              >
                {resetAgreementTemplate.isPending
                  ? 'Restoring…'
                  : agreementTemplate.data?.source === 'custom'
                    ? 'Restore built-in template'
                    : 'Discard unsaved edits'}
              </button>
            </div>
          </form>
          {templateMessage && (
            <p className="inline-note" role="status">
              {templateMessage}
            </p>
          )}
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
            A backup includes a transaction-consistent SQLite copy, the active agreement template,
            local settings, legacy records, and generated PDFs.
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
            profile details, the custom agreement template, application preferences, and imported
            legacy records. Existing activity logs are cleared and the built-in agreement becomes
            active again. Reference counters remain so previously used references are never reused.
            This only affects the configured Contract Studio data folder; backups and original
            source files stored elsewhere remain untouched.
          </p>
          <button
            className="button button--danger"
            type="button"
            disabled={clearData.isPending || update.isPending}
            onClick={() => {
              const confirmed = window.confirm(
                'This is irreversible.\n\nThis permanently removes all clients, contracts, bookings, invoices, payments, saved PDFs, your photographer profile, the custom agreement template, application preferences, imported legacy records, and existing activity logs from the configured Contract Studio data folder. The built-in agreement becomes active again. Reference counters stay in place so previously used references are never reused. Download a backup first. Backups and original source files stored elsewhere are not affected.\n\nClear all history and data now?',
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
                ? 'Local records, documents, settings, and activity logs have been cleared. The built-in agreement is active; reference counters were retained.'
                : 'Records were cleared, but some local files, database space, or logs could not be fully removed. Close other Contract Studio windows and retry the reset.'}
            </p>
          )}
        </Panel>
      </div>
    </>
  )
}
