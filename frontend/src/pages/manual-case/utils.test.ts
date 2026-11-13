import { describe, expect, it } from 'vitest'
import { EMPTY_FORM, buildPayload, payloadToForm } from './utils'
import type { ManualFormState } from './utils'

function form(overrides: Partial<ManualFormState> = {}): ManualFormState {
  return { ...EMPTY_FORM, ...overrides }
}

describe('buildPayload', () => {
  it('trims text fields and parses numeric inputs', () => {
    const payload = buildPayload(
      form({
        company_name: ' Acme ',
        report_year: '2023',
        reporting_period_label: ' FY2023 ',
        source_url: ' https://acme.com/report ',
        scope1_co2e_tonnes: '1,234.5',
        scope2_co2e_tonnes: '200',
        scope2_basis: 'market',
        scope3_co2e_tonnes: '  ',
        renewable_energy_pct: '45.5',
        taxonomy_aligned_revenue_pct: '30',
        taxonomy_aligned_capex_pct: '12.5',
        total_employees: '1,000',
        female_pct: '40',
        energy_consumption_mwh: '5,000',
        water_usage_m3: '900',
        waste_recycled_pct: '75',
        primary_activities: ' solar, wind ,, ',
      })
    )

    expect(payload).toMatchObject({
      company_name: 'Acme',
      report_year: 2023,
      reporting_period_label: 'FY2023',
      reporting_period_type: 'annual',
      source_document_type: 'manual_case',
      source_url: 'https://acme.com/report',
      scope1_co2e_tonnes: 1234.5,
      scope2_co2e_tonnes: 200,
      scope2_basis: 'market',
      scope3_co2e_tonnes: null,
      renewable_energy_pct: 45.5,
      taxonomy_aligned_revenue_pct: 30,
      taxonomy_aligned_capex_pct: 12.5,
      total_employees: 1000,
      female_pct: 40,
      energy_consumption_mwh: 5000,
      water_usage_m3: 900,
      waste_recycled_pct: 75,
      primary_activities: ['solar', 'wind'],
      evidence_summary: [],
    })
  })

  it('maps blank and non-finite numbers to null', () => {
    const payload = buildPayload(
      form({
        scope1_co2e_tonnes: 'abc',
        scope2_co2e_tonnes: '',
        scope3_co2e_tonnes: 'Infinity',
        renewable_energy_pct: '   ',
      })
    )

    expect(payload.scope1_co2e_tonnes).toBeNull()
    expect(payload.scope2_co2e_tonnes).toBeNull()
    expect(payload.scope3_co2e_tonnes).toBeNull()
    expect(payload.renewable_energy_pct).toBeNull()
  })

  it('keeps only market or location as the scope 2 basis', () => {
    expect(buildPayload(form({ scope2_basis: 'location' })).scope2_basis).toBe('location')
    expect(buildPayload(form({ scope2_basis: 'grid' })).scope2_basis).toBeNull()
  })

  it('falls back to the current year when the year is not numeric', () => {
    expect(buildPayload(form({ report_year: 'not-a-year' })).report_year).toBe(
      new Date().getFullYear()
    )
  })

  it('treats a blank year string as numeric zero', () => {
    expect(buildPayload(form({ report_year: '' })).report_year).toBe(0)
    expect(buildPayload(form({ report_year: '   ' })).report_year).toBe(0)
  })

  it('applies the form defaults for an empty form', () => {
    const payload = buildPayload(EMPTY_FORM)
    expect(payload).toMatchObject({
      company_name: '',
      report_year: 0,
      reporting_period_type: 'annual',
      source_document_type: 'manual_case',
      source_url: null,
      reporting_period_label: null,
      primary_activities: [],
      evidence_summary: [],
      total_revenue_eur: null,
      total_capex_eur: null,
    })
  })
})

describe('payloadToForm', () => {
  it('returns the empty form for an empty payload', () => {
    expect(payloadToForm({})).toEqual(EMPTY_FORM)
  })

  it('round-trips a populated payload back into string fields', () => {
    const payload = buildPayload(
      form({
        company_name: 'Acme',
        report_year: '2023',
        scope1_co2e_tonnes: '1,234.5',
        scope2_basis: 'market',
        primary_activities: 'solar, wind',
      })
    )

    expect(payloadToForm(payload)).toMatchObject({
      company_name: 'Acme',
      report_year: '2023',
      scope1_co2e_tonnes: '1234.5',
      scope2_basis: 'market',
      primary_activities: 'solar, wind',
    })
  })

  it('drops unsupported scope 2 basis values', () => {
    expect(payloadToForm({ scope2_basis: null }).scope2_basis).toBe('')
    expect(payloadToForm({}).scope2_basis).toBe('')
  })

  it('preserves explicit zero values as strings', () => {
    const result = payloadToForm({
      report_year: 0,
      scope1_co2e_tonnes: 0,
      total_employees: 0,
    })
    expect(result.report_year).toBe('0')
    expect(result.scope1_co2e_tonnes).toBe('0')
    expect(result.total_employees).toBe('0')
  })
})
