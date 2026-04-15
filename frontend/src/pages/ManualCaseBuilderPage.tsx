import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, FileJson, PencilLine, Save } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { QueryStateCard } from '@/components/QueryStateCard'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { createManualReport, listCompanies } from '@/lib/api'
import type { ManualReportInput } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'
import { findNaceOption, NACE_OPTIONS } from '@/lib/nace-codes'

type ManualFormState = {
  company_name: string
  report_year: string
  reporting_period_label: string
  reporting_period_type: string
  source_document_type: string
  source_url: string
  scope1_co2e_tonnes: string
  scope2_co2e_tonnes: string
  scope3_co2e_tonnes: string
  renewable_energy_pct: string
  taxonomy_aligned_revenue_pct: string
  taxonomy_aligned_capex_pct: string
  total_employees: string
  female_pct: string
  energy_consumption_mwh: string
  water_usage_m3: string
  waste_recycled_pct: string
  primary_activities: string
}

const EMPTY_FORM: ManualFormState = {
  company_name: '',
  report_year: '',
  reporting_period_label: '',
  reporting_period_type: 'annual',
  source_document_type: 'manual_case',
  source_url: '',
  scope1_co2e_tonnes: '',
  scope2_co2e_tonnes: '',
  scope3_co2e_tonnes: '',
  renewable_energy_pct: '',
  taxonomy_aligned_revenue_pct: '',
  taxonomy_aligned_capex_pct: '',
  total_employees: '',
  female_pct: '',
  energy_consumption_mwh: '',
  water_usage_m3: '',
  waste_recycled_pct: '',
  primary_activities: '',
}

function parseOptionalNumber(value: string) {
  const trimmed = value.trim()
  if (!trimmed) return null
  const normalized = trimmed.replace(/,/g, '')
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

function buildPayload(form: ManualFormState): ManualReportInput {
  const reportYear = Number(form.report_year)

  return {
    company_name: form.company_name.trim(),
    report_year: Number.isFinite(reportYear) ? reportYear : new Date().getFullYear(),
    reporting_period_label: form.reporting_period_label.trim() || null,
    reporting_period_type: form.reporting_period_type || 'annual',
    source_document_type: form.source_document_type || 'manual_case',
    source_url: form.source_url.trim() || null,
    scope1_co2e_tonnes: parseOptionalNumber(form.scope1_co2e_tonnes),
    scope2_co2e_tonnes: parseOptionalNumber(form.scope2_co2e_tonnes),
    scope3_co2e_tonnes: parseOptionalNumber(form.scope3_co2e_tonnes),
    energy_consumption_mwh: parseOptionalNumber(form.energy_consumption_mwh),
    renewable_energy_pct: parseOptionalNumber(form.renewable_energy_pct),
    water_usage_m3: parseOptionalNumber(form.water_usage_m3),
    waste_recycled_pct: parseOptionalNumber(form.waste_recycled_pct),
    total_revenue_eur: null,
    taxonomy_aligned_revenue_pct: parseOptionalNumber(form.taxonomy_aligned_revenue_pct),
    total_capex_eur: null,
    taxonomy_aligned_capex_pct: parseOptionalNumber(form.taxonomy_aligned_capex_pct),
    total_employees: parseOptionalNumber(form.total_employees),
    female_pct: parseOptionalNumber(form.female_pct),
    primary_activities: form.primary_activities
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
    evidence_summary: [],
  }
}

function payloadToForm(payload: Partial<ManualReportInput>): ManualFormState {
  return {
    company_name: payload.company_name ?? '',
    report_year: payload.report_year != null ? String(payload.report_year) : '',
    reporting_period_label: payload.reporting_period_label ?? '',
    reporting_period_type: payload.reporting_period_type ?? 'annual',
    source_document_type: payload.source_document_type ?? 'manual_case',
    source_url: payload.source_url ?? '',
    scope1_co2e_tonnes:
      payload.scope1_co2e_tonnes != null ? String(payload.scope1_co2e_tonnes) : '',
    scope2_co2e_tonnes:
      payload.scope2_co2e_tonnes != null ? String(payload.scope2_co2e_tonnes) : '',
    scope3_co2e_tonnes:
      payload.scope3_co2e_tonnes != null ? String(payload.scope3_co2e_tonnes) : '',
    renewable_energy_pct:
      payload.renewable_energy_pct != null ? String(payload.renewable_energy_pct) : '',
    taxonomy_aligned_revenue_pct:
      payload.taxonomy_aligned_revenue_pct != null
        ? String(payload.taxonomy_aligned_revenue_pct)
        : '',
    taxonomy_aligned_capex_pct:
      payload.taxonomy_aligned_capex_pct != null ? String(payload.taxonomy_aligned_capex_pct) : '',
    total_employees: payload.total_employees != null ? String(payload.total_employees) : '',
    female_pct: payload.female_pct != null ? String(payload.female_pct) : '',
    energy_consumption_mwh:
      payload.energy_consumption_mwh != null ? String(payload.energy_consumption_mwh) : '',
    water_usage_m3: payload.water_usage_m3 != null ? String(payload.water_usage_m3) : '',
    waste_recycled_pct:
      payload.waste_recycled_pct != null ? String(payload.waste_recycled_pct) : '',
    primary_activities: payload.primary_activities?.join(', ') ?? '',
  }
}

export function ManualCaseBuilderPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<ManualFormState>(EMPTY_FORM)
  const [industryCode, setIndustryCode] = useState<string>('')
  const [draftJson, setDraftJson] = useState('')
  const [jsonError, setJsonError] = useState<string | null>(null)

  const {
    data: companies = [],
    isLoading: companiesLoading,
    error: companiesError,
    refetch: refetchCompanies,
  } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const recentCompanies = useMemo(() => {
    const seen = new Set<string>()
    return companies.filter((item) => {
      if (seen.has(item.company_name)) return false
      seen.add(item.company_name)
      return true
    }).slice(0, 6)
  }, [companies])

  const selectedIndustry = useMemo(() => findNaceOption(industryCode), [industryCode])

  const previewPayload = useMemo(() => {
    const payload = buildPayload(form)
    if (selectedIndustry) {
      payload.industry_code = selectedIndustry.code
      payload.industry_sector = selectedIndustry.sectorEn
    }
    return payload
  }, [form, selectedIndustry])

  const saveMutation = useMutation({
    mutationFn: (data: ManualReportInput) =>
      createManualReport(
        data,
        selectedIndustry
          ? {
              industryCode: selectedIndustry.code,
              industrySector: selectedIndustry.sectorEn,
            }
          : undefined
      ),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['companies'] })
      queryClient.invalidateQueries({ queryKey: ['company-profile', result.company_name] })
      navigate(`/companies/${encodeURIComponent(result.company_name)}`)
    },
  })

  const setField = (key: keyof ManualFormState, value: string) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const importDraft = () => {
    try {
      const parsed = JSON.parse(draftJson) as Partial<ManualReportInput>
      setForm(payloadToForm(parsed))
      setIndustryCode(typeof parsed.industry_code === 'string' ? parsed.industry_code : '')
      setJsonError(null)
    } catch {
      setJsonError(t('manual.invalidJson'))
    }
  }

  const handleSave = () => {
    if (!form.company_name.trim() || !form.report_year.trim()) {
      return
    }
    saveMutation.mutate(previewPayload)
  }

  const canSave = form.company_name.trim().length > 0 && form.report_year.trim().length > 0

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900">
        {t('projectAnalysis.modeBanner')}
      </div>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <p className="section-kicker">{t('manual.kicker')}</p>
          <Badge variant="secondary" className="w-fit bg-amber-100 text-amber-900">
            {t('manual.badge')}
          </Badge>
          <h1 className="text-3xl font-semibold text-slate-900">
            {t('manual.title')}
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-600">
            {t('manual.subtitle')}
          </p>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 lg:max-w-sm">
          {t('manual.storageHint')}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.45fr_0.95fr]">
        <div className="space-y-4">
          <Card className="surface-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <PencilLine size={16} className="text-amber-700" />
                {t('manual.formTitle')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="company_name">{t('common.company')}</Label>
                  <Input
                    id="company_name"
                    value={form.company_name}
                    onChange={(e) => setField('company_name', e.target.value)}
                    placeholder={t('manual.companyPlaceholder')}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="report_year">{t('common.year')}</Label>
                  <Input
                    id="report_year"
                    value={form.report_year}
                    onChange={(e) => setField('report_year', e.target.value)}
                    placeholder="2025"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reporting_period_label">{t('manual.periodLabel')}</Label>
                  <Input
                    id="reporting_period_label"
                    value={form.reporting_period_label}
                    onChange={(e) => setField('reporting_period_label', e.target.value)}
                    placeholder="FY2025"
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t('manual.periodType')}</Label>
                  <Select
                    value={form.reporting_period_type}
                    onValueChange={(value) => setField('reporting_period_type', value)}
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
                    onValueChange={(value) => setField('source_document_type', value)}
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
                    onChange={(e) => setField('source_url', e.target.value)}
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
                        {i18n.resolvedLanguage?.startsWith('de')
                          ? option.sectorDe
                          : option.sectorEn}
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
                  {[
                    ['scope1_co2e_tonnes', t('companies.scope1')],
                    ['scope2_co2e_tonnes', t('companies.scope2')],
                    ['scope3_co2e_tonnes', t('manual.scope3')],
                    ['renewable_energy_pct', t('companies.renewable')],
                    ['taxonomy_aligned_revenue_pct', t('manual.taxonomyRevenue')],
                    ['taxonomy_aligned_capex_pct', t('manual.taxonomyCapex')],
                    ['total_employees', t('companies.employees')],
                    ['female_pct', t('manual.femalePct')],
                    ['energy_consumption_mwh', t('manual.energy')],
                    ['water_usage_m3', t('manual.water')],
                    ['waste_recycled_pct', t('manual.waste')],
                  ].map(([key, label]) => (
                    <div key={key} className="space-y-2">
                      <Label htmlFor={key}>{label}</Label>
                      <Input
                        id={key}
                        value={form[key as keyof ManualFormState]}
                        onChange={(e) => setField(key as keyof ManualFormState, e.target.value)}
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
                    onChange={(e) => setField('primary_activities', e.target.value)}
                    placeholder={t('manual.activitiesPlaceholder')}
                    className="min-h-24 w-full rounded-md border border-input bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  />
                </div>
              </div>

              <div className="rounded-xl border border-dashed border-stone-300 bg-stone-50 px-4 py-4 text-xs leading-5 text-slate-600">
                {t('manual.overwriteHint')}
              </div>

              <div className="flex flex-wrap gap-3">
                <Button onClick={handleSave} disabled={!canSave || saveMutation.isPending}>
                  <Save size={14} />
                  {saveMutation.isPending ? t('manual.saving') : t('manual.saveCase')}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setForm(EMPTY_FORM)
                    setIndustryCode('')
                  }}
                  disabled={saveMutation.isPending}
                >
                  {t('manual.reset')}
                </Button>
                {saveMutation.error && (
                  <p className="self-center text-sm text-red-600">
                    {localizeErrorMessage(t, saveMutation.error, 'common.error')}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="surface-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ArrowRight size={16} className="text-amber-700" />
                {t('manual.recentCompanies')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {companiesLoading ? (
                <QueryStateCard
                  tone="loading"
                  title={t('common.loading')}
                  body={t('manual.recentCompanies')}
                />
              ) : companiesError ? (
                <QueryStateCard
                  tone="error"
                  title={t('common.error')}
                  body={localizeErrorMessage(t, companiesError, 'common.error')}
                  actionLabel={t('errorBoundary.retry')}
                  onAction={() => void refetchCompanies()}
                />
              ) : recentCompanies.length === 0 ? (
                <p className="text-sm text-slate-500">{t('manual.noCompaniesYet')}</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {recentCompanies.map((company) => (
                    <button
                      key={company.company_name}
                      type="button"
                      onClick={() =>
                        setForm((current) => ({
                          ...current,
                          company_name: company.company_name,
                        }))
                      }
                      className="rounded-full border bg-white px-3 py-1.5 text-left text-sm leading-5 text-slate-700 hover:border-amber-300 hover:text-amber-800"
                    >
                      {company.company_name}
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="surface-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileJson size={16} className="text-amber-700" />
                {t('manual.jsonTitle')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <textarea
                value={draftJson}
                onChange={(e) => setDraftJson(e.target.value)}
                placeholder={t('manual.jsonPlaceholder')}
                className="min-h-40 w-full rounded-md border border-input bg-white px-3 py-2 font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
              <div className="flex gap-3">
                <Button variant="outline" onClick={importDraft}>
                  {t('manual.importJson')}
                </Button>
                {jsonError && <p className="self-center text-sm text-red-600">{jsonError}</p>}
              </div>
            </CardContent>
          </Card>

          <Card className="surface-card">
            <CardHeader>
              <CardTitle className="text-base">{t('manual.previewTitle')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <pre className="max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">
                {JSON.stringify(previewPayload, null, 2)}
              </pre>
              <div className="flex gap-3">
                <Button asChild variant="outline">
                  <Link to="/companies">{t('manual.viewCompanies')}</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
