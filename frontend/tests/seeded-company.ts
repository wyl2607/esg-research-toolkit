import { expect, type APIRequestContext, type TestInfo } from '@playwright/test'

import type { ManualReportInput } from '../src/lib/types'

export type SeededCompany = {
  companyName: string
  reportYear: number
  optionLabel: string
  profilePath: string
  payload: ManualReportInput
}

const BASE_REPORT_YEAR = 2025

const BASE_SEEDED_REPORT: Omit<
  ManualReportInput,
  'company_name' | 'report_year' | 'reporting_period_label' | 'source_url'
> = {
  reporting_period_type: 'annual',
  source_document_type: 'manual_case',
  scope1_co2e_tonnes: 14250,
  scope2_co2e_tonnes: 6840,
  scope3_co2e_tonnes: 58200,
  energy_consumption_mwh: 194000,
  renewable_energy_pct: 47.5,
  water_usage_m3: 98000,
  waste_recycled_pct: 76.4,
  total_revenue_eur: 640000000,
  taxonomy_aligned_revenue_pct: 32.1,
  total_capex_eur: 215000000,
  taxonomy_aligned_capex_pct: 38.4,
  total_employees: 12800,
  female_pct: 41.2,
  primary_activities: ['battery manufacturing', 'grid storage'],
  evidence_summary: [],
}

export async function seedManualCompany(
  request: APIRequestContext,
  testInfo: TestInfo,
  overrides: Partial<ManualReportInput> = {}
): Promise<SeededCompany> {
  const seeded = buildSeededCompany(testInfo, overrides)

  await deleteSeededCompany(request, seeded, { allowMissing: true })

  const response = await request.post('/api/report/manual', {
    data: seeded.payload,
  })

  await expectOkResponse(
    response,
    `Seeding manual company failed for ${seeded.companyName} (${seeded.reportYear})`
  )

  await testInfo.attach('seeded-company.json', {
    body: JSON.stringify(seeded.payload, null, 2),
    contentType: 'application/json',
  })

  return seeded
}

export async function deleteSeededCompany(
  request: APIRequestContext,
  seeded: SeededCompany,
  options: { allowMissing?: boolean } = {}
) {
  const response = await request.delete(
    `/api/report/companies/${encodeURIComponent(seeded.companyName)}/${seeded.reportYear}?hard=true`
  )

  if (options.allowMissing && response.status() === 404) {
    return
  }

  await expectOkResponse(
    response,
    `Cleaning seeded company failed for ${seeded.companyName} (${seeded.reportYear})`
  )
}

export async function addManualSourceToSeededCompany(
  request: APIRequestContext,
  seeded: SeededCompany,
  overrides: Partial<ManualReportInput> = {}
) {
  const response = await request.post('/api/report/manual', {
    data: {
      ...seeded.payload,
      ...overrides,
      company_name: seeded.companyName,
      report_year: seeded.reportYear,
      reporting_period_label:
        overrides.reporting_period_label ?? seeded.payload.reporting_period_label,
    },
  })

  await expectOkResponse(
    response,
    `Adding manual source failed for ${seeded.companyName} (${seeded.reportYear})`
  )
}

function buildSeededCompany(
  testInfo: TestInfo,
  overrides: Partial<ManualReportInput>
): SeededCompany {
  const slug = slugify(`${testInfo.project.name}-${testInfo.title}`)
  const companyName = overrides.company_name ?? `Playwright Analyst ${slug}`
  const reportYear = overrides.report_year ?? BASE_REPORT_YEAR
  const reportingPeriodLabel = overrides.reporting_period_label ?? `FY ${reportYear}`

  const payload: ManualReportInput = {
    ...BASE_SEEDED_REPORT,
    ...overrides,
    company_name: companyName,
    report_year: reportYear,
    reporting_period_label: reportingPeriodLabel,
    source_url: overrides.source_url ?? `https://playwright.seed/${slug}`,
  }

  return {
    companyName,
    reportYear,
    optionLabel: `${companyName} (${reportYear})`,
    profilePath: `/companies/${encodeURIComponent(companyName)}`,
    payload,
  }
}

async function expectOkResponse(response: Awaited<ReturnType<APIRequestContext['fetch']>>, message: string) {
  if (response.ok()) {
    return
  }

  const body = await response.text()
  expect(response.ok(), `${message}: HTTP ${response.status()} ${body}`).toBeTruthy()
}

function slugify(value: string) {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48)

  return slug || 'seeded-company'
}
