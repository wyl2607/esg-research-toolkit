import { PencilLine, Save } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { NoticeBanner } from '@/components/NoticeBanner'
import { Panel } from '@/components/layout/Panel'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { localizeErrorMessage } from '@/lib/error-utils'
import { NACE_OPTIONS } from '@/lib/nace-codes'
import type { ManualFormState } from '@/pages/manual-case/utils'

interface ManualCaseFormPanelProps {
  form: ManualFormState
  industryCode: string
  setIndustryCode: (value: string) => void
  onFieldChange: (key: keyof ManualFormState, value: string) => void
  onSave: () => void
  onReset: () => void
  canSave: boolean
  isSaving: boolean
  saveError: unknown
}

const METRIC_FIELDS: Array<{ key: keyof ManualFormState; labelKey: string }> = [
  { key: 'scope1_co2e_tonnes', labelKey: 'companies.scope1' },
  { key: 'scope2_co2e_tonnes', labelKey: 'companies.scope2' },
  { key: 'scope3_co2e_tonnes', labelKey: 'manual.scope3' },
  { key: 'renewable_energy_pct', labelKey: 'companies.renewable' },
  { key: 'taxonomy_aligned_revenue_pct', labelKey: 'manual.taxonomyRevenue' },
  { key: 'taxonomy_aligned_capex_pct', labelKey: 'manual.taxonomyCapex' },
  { key: 'total_employees', labelKey: 'companies.employees' },
  { key: 'female_pct', labelKey: 'manual.femalePct' },
  { key: 'energy_consumption_mwh', labelKey: 'manual.energy' },
  { key: 'water_usage_m3', labelKey: 'manual.water' },
  { key: 'waste_recycled_pct', labelKey: 'manual.waste' },
]

export function ManualCaseFormPanel({
  form,
  industryCode,
  setIndustryCode,
  onFieldChange,
  onSave,
  onReset,
  canSave,
  isSaving,
  saveError,
}: ManualCaseFormPanelProps) {
  const { t, i18n } = useTranslation()

  return (
    <Panel
      title={(
        <span className="flex items-center gap-2 text-base">
          <PencilLine size={16} className="text-amber-700" />
          {t('manual.formTitle')}
        </span>
      )}
    >
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="company_name">{t('common.company')}</Label>
            <Input
              id="company_name"
              value={form.company_name}
              onChange={(e) => onFieldChange('company_name', e.target.value)}
              placeholder={t('manual.companyPlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="report_year">{t('common.year')}</Label>
            <Input
              id="report_year"
              value={form.report_year}
              onChange={(e) => onFieldChange('report_year', e.target.value)}
              placeholder="2025"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="reporting_period_label">{t('manual.periodLabel')}</Label>
            <Input
              id="reporting_period_label"
              value={form.reporting_period_label}
              onChange={(e) => onFieldChange('reporting_period_label', e.target.value)}
              placeholder="FY2025"
            />
          </div>
          <div className="space-y-2">
            <Label>{t('manual.periodType')}</Label>
            <Select
              value={form.reporting_period_type}
              onValueChange={(value) => onFieldChange('reporting_period_type', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('manual.periodType')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="annual">{t('manual.periodAnnual')}</SelectItem>
                <SelectItem value="quarterly">{t('manual.periodQuarterly')}</SelectItem>
                <SelectItem value="event">{t('manual.periodEvent')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>{t('manual.sourceType')}</Label>
            <Select
              value={form.source_document_type}
              onValueChange={(value) => onFieldChange('source_document_type', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder={t('manual.sourceType')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manual_case">{t('manual.sourceManual')}</SelectItem>
                <SelectItem value="annual_report">{t('manual.sourceAnnual')}</SelectItem>
                <SelectItem value="sustainability_report">{t('manual.sourceSustainability')}</SelectItem>
                <SelectItem value="filing">{t('manual.sourceFiling')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="source_url">{t('manual.sourceUrl')}</Label>
            <Input
              id="source_url"
              value={form.source_url}
              onChange={(e) => onFieldChange('source_url', e.target.value)}
              placeholder="https://example.com/report"
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="manual-industry-code">{t('upload.industryLabel')}</Label>
            <select
              id="manual-industry-code"
              className="h-10 w-full rounded-xl border border-stone-200 bg-white px-3 text-sm"
              value={industryCode}
              onChange={(e) => setIndustryCode(e.target.value)}
            >
              <option value="">{t('upload.industryNone')}</option>
              {NACE_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.code} —{' '}
                  {i18n.resolvedLanguage?.startsWith('de') ? option.sectorDe : option.sectorEn}
                </option>
              ))}
            </select>
            <p className="text-xs text-stone-500">{t('upload.industryHint')}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">{t('manual.metricsTitle')}</h2>
            <p className="text-xs text-slate-500">{t('manual.metricsHint')}</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {METRIC_FIELDS.map(({ key, labelKey }) => (
              <div key={key} className="space-y-2">
                <Label htmlFor={key}>{t(labelKey)}</Label>
                <Input
                  id={key}
                  value={form[key]}
                  onChange={(e) => onFieldChange(key, e.target.value)}
                  placeholder="—"
                />
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <Label htmlFor="primary_activities">{t('manual.activities')}</Label>
            <textarea
              id="primary_activities"
              value={form.primary_activities}
              onChange={(e) => onFieldChange('primary_activities', e.target.value)}
              placeholder={t('manual.activitiesPlaceholder')}
              className="min-h-24 w-full rounded-md border border-input bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
        </div>

        <NoticeBanner tone="warning">
          {t('manual.overwriteHint')}
        </NoticeBanner>

        <div className="flex flex-wrap gap-3">
          <Button onClick={onSave} disabled={!canSave || isSaving}>
            <Save size={14} />
            {isSaving ? t('manual.saving') : t('manual.saveCase')}
          </Button>
          <Button variant="outline" onClick={onReset} disabled={isSaving}>
            {t('manual.reset')}
          </Button>
          {saveError != null && (
            <p className="self-center text-sm text-red-600">
              {localizeErrorMessage(t, saveError, 'common.error')}
            </p>
          )}
        </div>
      </div>
    </Panel>
  )
}
