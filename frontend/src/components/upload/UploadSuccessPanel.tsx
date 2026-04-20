import { CheckCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { Panel } from '@/components/layout/Panel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { CompanyESGData } from '@/lib/types'

interface UploadSuccessPanelProps {
  result: CompanyESGData
}

export function UploadSuccessPanel({ result }: UploadSuccessPanelProps) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

  const fields: [string, string][] = [
    [
      t('companies.scope1'),
      result.scope1_co2e_tonnes != null
        ? `${result.scope1_co2e_tonnes.toLocaleString(i18n.resolvedLanguage)} t`
        : '—',
    ],
    [
      t('companies.scope2'),
      result.scope2_co2e_tonnes != null
        ? `${result.scope2_co2e_tonnes.toLocaleString(i18n.resolvedLanguage)} t`
        : '—',
    ],
    [
      t('upload.renewableEnergy'),
      result.renewable_energy_pct != null ? `${result.renewable_energy_pct.toFixed(1)}%` : '—',
    ],
    [
      t('companies.employees'),
      result.total_employees?.toLocaleString(i18n.resolvedLanguage) ?? '—',
    ],
    [
      t('upload.taxonomyAligned'),
      result.taxonomy_aligned_revenue_pct != null
        ? `${result.taxonomy_aligned_revenue_pct.toFixed(1)}%`
        : '—',
    ],
    [t('common.summary'), result.primary_activities.join(', ') || '—'],
  ]

  return (
    <Panel>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <CheckCircle size={18} className="text-green-500" />
          <span className="font-semibold">
            {t('upload.success')}: {result.company_name} ({result.report_year})
          </span>
        </div>
        <div className="grid gap-3 text-sm md:grid-cols-2">
          {fields.map(([k, v]) => (
            <div
              key={k}
              className="flex justify-between rounded-xl border border-stone-200 bg-white/80 px-3 py-3"
            >
              <span className="text-slate-500">{k}</span>
              <Badge variant="secondary" className="bg-stone-100 text-slate-700">
                {v}
              </Badge>
            </div>
          ))}
        </div>
        <div className="flex gap-3">
          <Button onClick={() => navigate('/taxonomy')}>{t('dashboard.runTaxonomy')}</Button>
          <Button variant="outline" onClick={() => navigate('/companies')}>
            {t('nav.companies')}
          </Button>
        </div>
      </div>
    </Panel>
  )
}
