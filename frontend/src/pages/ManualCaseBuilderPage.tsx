import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, FileJson } from 'lucide-react'

import { ManualCaseFormPanel } from '@/components/manual-case/ManualCaseFormPanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { QueryStateCard } from '@/components/QueryStateCard'
import { NoticeBanner } from '@/components/NoticeBanner'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { createManualReport, listCompanies } from '@/lib/api'
import type { ManualReportInput } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'
import { findNaceOption } from '@/lib/nace-codes'
import { EMPTY_FORM, buildPayload, payloadToForm, type ManualFormState } from '@/pages/manual-case/utils'

export function ManualCaseBuilderPage() {
  const { t } = useTranslation()
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
    <PageContainer>
      <NoticeBanner tone="mode">
        {t('projectAnalysis.modeBanner')}
      </NoticeBanner>
      <PageHeader
        title={t('manual.title')}
        subtitle={t('manual.subtitle')}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-[0.14em] text-slate-500">
              {t('manual.kicker')}
            </span>
            <Badge variant="secondary" className="w-fit bg-amber-100 text-amber-900">
              {t('manual.badge')}
            </Badge>
          </div>
        )}
      />
      <NoticeBanner tone="warning">
        <div className="text-sm">
          {t('manual.storageHint')}
        </div>
      </NoticeBanner>

      <div className="grid gap-4 lg:grid-cols-[1.45fr_0.95fr]">
        <div className="space-y-4">
          <ManualCaseFormPanel
            form={form}
            industryCode={industryCode}
            setIndustryCode={setIndustryCode}
            onFieldChange={setField}
            onSave={handleSave}
            onReset={() => {
              setForm(EMPTY_FORM)
              setIndustryCode('')
            }}
            canSave={canSave}
            isSaving={saveMutation.isPending}
            saveError={saveMutation.error}
          />
        </div>

        <div className="space-y-4">
          <Panel
            title={(
              <span className="flex items-center gap-2 text-base">
                <ArrowRight size={16} className="text-amber-700" />
                {t('manual.recentCompanies')}
              </span>
            )}
          >
            <div className="space-y-3">
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
            </div>
          </Panel>

          <Panel
            title={(
              <span className="flex items-center gap-2 text-base">
                <FileJson size={16} className="text-amber-700" />
                {t('manual.jsonTitle')}
              </span>
            )}
          >
            <div className="space-y-3">
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
            </div>
          </Panel>

          <Panel title={t('manual.previewTitle')}>
            <div className="space-y-3">
              <pre className="max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">
                {JSON.stringify(previewPayload, null, 2)}
              </pre>
              <div className="flex gap-3">
                <Button asChild variant="outline">
                  <Link to="/companies">{t('manual.viewCompanies')}</Link>
                </Button>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </PageContainer>
  )
}
