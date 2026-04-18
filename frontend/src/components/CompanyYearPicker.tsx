import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Check, Upload } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { CompanyYearCoverage } from '@/lib/api'

export interface CompanyYearSelection {
  company: string | null
  year: number | null
}

interface Props {
  companies: CompanyYearCoverage[]
  value: CompanyYearSelection
  onChange: (next: CompanyYearSelection) => void
  companyLabel?: string
  yearLabel?: string
  /**
   * Behaviour when the user picks a year that is NOT in imported_years.
   * Default: redirect to `/upload?company=X&year=Y` (design doc D1=b).
   */
  onNotImportedYear?: (company: string, year: number) => void
  /** ID prefix so multiple pickers on one page stay unique. */
  idPrefix?: string
}

/**
 * Two-step picker: choose a company, then choose a year.
 *
 * Years are rendered in two groups: "imported" (data already in DB, clickable
 * into the current page) and "not imported" (no row — by default clicking
 * one deep-links to the Upload page prefilled with company + year so the
 * user can add a PDF).
 *
 * Design doc: docs/design-docs/company_year_dual_picker.md
 */
export function CompanyYearPicker({
  companies,
  value,
  onChange,
  companyLabel,
  yearLabel,
  onNotImportedYear,
  idPrefix = 'company-year-picker',
}: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const selected = useMemo(
    () => companies.find((c) => c.company_name === value.company) ?? null,
    [companies, value.company],
  )

  const importedSet = useMemo(
    () => new Set(selected?.imported_years ?? []),
    [selected],
  )

  const handleYear = (yearStr: string) => {
    const year = Number(yearStr)
    if (!selected) return
    if (importedSet.has(year)) {
      onChange({ company: selected.company_name, year })
      return
    }
    // Not-imported path
    if (onNotImportedYear) {
      onNotImportedYear(selected.company_name, year)
      return
    }
    const qs = new URLSearchParams({
      company: selected.company_name,
      year: String(year),
    })
    navigate(`/upload?${qs.toString()}`)
  }

  return (
    <div className="grid gap-3 sm:grid-cols-[1.2fr_1fr]">
      <div className="space-y-1.5">
        <label
          htmlFor={`${idPrefix}-company`}
          className="text-xs font-medium uppercase tracking-wide text-slate-500"
        >
          {companyLabel ?? t('common.company')}
        </label>
        <Select
          value={value.company ?? ''}
          onValueChange={(v) => onChange({ company: v, year: null })}
        >
          <SelectTrigger
            id={`${idPrefix}-company`}
            className="h-12 w-full text-base"
          >
            <SelectValue placeholder={t('common.selectCompany')} />
          </SelectTrigger>
          <SelectContent>
            {companies.map((c) => (
              <SelectItem key={c.company_name} value={c.company_name}>
                {c.company_name}
                {c.imported_years.length > 0 ? (
                  <span className="ml-2 text-xs text-slate-400">
                    {c.imported_years.length}{' '}
                    {t('companyYearPicker.yearsImportedShort')}
                  </span>
                ) : null}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <label
          htmlFor={`${idPrefix}-year`}
          className="text-xs font-medium uppercase tracking-wide text-slate-500"
        >
          {yearLabel ?? t('common.year')}
        </label>
        <Select
          value={value.year ? String(value.year) : ''}
          onValueChange={handleYear}
          disabled={!selected}
        >
          <SelectTrigger
            id={`${idPrefix}-year`}
            className="h-12 w-full text-base"
            aria-controls={`${idPrefix}-year-menu`}
          >
            <SelectValue
              placeholder={
                selected
                  ? t('companyYearPicker.selectYear')
                  : t('companyYearPicker.selectCompanyFirst')
              }
            />
          </SelectTrigger>
          <SelectContent id={`${idPrefix}-year-menu`}>
            {(selected?.suggested_years ?? []).map((year) => {
              const imported = importedSet.has(year)
              return (
                <SelectItem
                  key={year}
                  value={String(year)}
                  className={
                    imported
                      ? 'text-slate-800'
                      : 'text-slate-400 hover:text-slate-600'
                  }
                >
                  <span className="flex items-center gap-2">
                    {imported ? (
                      <Check
                        size={12}
                        className="shrink-0 text-emerald-600"
                        aria-hidden
                      />
                    ) : (
                      <Upload
                        size={12}
                        className="shrink-0 text-slate-400"
                        aria-hidden
                      />
                    )}
                    <span>{year}</span>
                    <span className="ml-auto text-[10px] uppercase tracking-wide">
                      {imported
                        ? t('companyYearPicker.imported')
                        : t('companyYearPicker.notImported')}
                    </span>
                  </span>
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
