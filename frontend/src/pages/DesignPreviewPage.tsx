/**
 * /design-preview — dev-only page for comparing new design system primitives.
 * Route registered in App.tsx. Not linked from Sidebar — access via URL.
 *
 * User opens http://localhost:5173/design-preview, scrolls, picks which
 * variant they want, and tells Claude. Claude then applies the chosen
 * variant as the locked default for Phase 2 page migration.
 */
import { type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel, StatCard } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { FilterBar } from '@/components/FilterBar'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'

function Section({ id, title, subtitle, children }: { id: string; title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section id={id} className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
          {id.toUpperCase()}
        </p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-900">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
      </div>
      <div className="rounded-3xl border-2 border-dashed border-slate-300 bg-white/60 p-6">
        {children}
      </div>
    </section>
  )
}

function VariantLabel({ label }: { label: string }) {
  return (
    <div className="mb-3 inline-flex items-center rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white">
      {label}
    </div>
  )
}

export function DesignPreviewPage() {
  const { t } = useTranslation()

  return (
    <PageContainer>
      <div className="rounded-3xl bg-gradient-to-br from-amber-50 to-stone-50 p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">
          {t('designPreview.hero.kicker')}
        </p>
        <h1 className="mt-2 text-4xl font-semibold text-slate-900">
          {t('designPreview.hero.title')}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          {t('designPreview.hero.subtitle')}
        </p>
        <nav className="mt-5 flex flex-wrap gap-2">
          {['header', 'stat-cards', 'banners', 'filter-bar', 'companies-mock'].map((id) => (
            <a
              key={id}
              href={`#${id}`}
              className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:border-amber-500 hover:text-amber-800"
            >
              {t(`designPreview.nav.${id}`)}
            </a>
          ))}
        </nav>
      </div>

      <Section
        id="header"
        title={t('designPreview.sections.header.title')}
        subtitle={t('designPreview.sections.header.subtitle')}
      >
        <div className="space-y-10">
          <div>
            <VariantLabel label={t('designPreview.variants.headerA')} />
            <PageHeader
              title={t('designPreview.samples.companiesTitle')}
              subtitle={t('designPreview.samples.companiesSubtitle')}
              actions={<Button variant="outline">{t('designPreview.actions.csvExport')}</Button>}
              kpis={[
                { label: t('designPreview.kpis.companies'), value: '36' },
                { label: t('designPreview.kpis.years'), value: '3' },
                { label: t('designPreview.kpis.datasets'), value: '36' },
              ]}
            />
          </div>

          <div>
            <VariantLabel label={t('designPreview.variants.headerB')} />
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-amber-700">
                {t('designPreview.samples.companiesKicker')}
              </p>
              <PageHeader
                title={t('designPreview.samples.companiesTitle')}
                subtitle={t('designPreview.samples.companiesSubtitle')}
                kpis={[
                  { label: t('designPreview.kpis.companies'), value: '36' },
                  { label: t('designPreview.kpis.years'), value: '3' },
                  { label: t('designPreview.kpis.datasets'), value: '36' },
                ]}
              />
            </div>
          </div>

          <div>
            <VariantLabel label={t('designPreview.variants.headerC')} />
            <PageHeader
              title={t('designPreview.samples.compareTitle')}
              subtitle={t('designPreview.samples.compareSubtitle')}
              actions={
                <div className="flex gap-2">
                  <Button variant="outline">{t('designPreview.actions.reset')}</Button>
                  <Button>{t('designPreview.actions.startCompare')}</Button>
                </div>
              }
            />
          </div>
        </div>
      </Section>

      <Section
        id="stat-cards"
        title={t('designPreview.sections.statCards.title')}
        subtitle={t('designPreview.sections.statCards.subtitle')}
      >
        <div className="space-y-10">
          <div>
            <VariantLabel label={t('designPreview.variants.statCardsA')} />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatCard label={t('designPreview.kpis.companies')} value="36" />
              <StatCard label={t('designPreview.statCards.avgTaxonomy')} value="20.8%" />
              <StatCard label={t('designPreview.statCards.avgRenewable')} value="50.5%" />
              <StatCard
                label={t('designPreview.kpis.years')}
                value="3"
                hint={t('designPreview.statCards.yearsHint')}
              />
            </div>
          </div>

          <div>
            <VariantLabel label={t('designPreview.variants.statCardsB')} />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                { l: t('designPreview.kpis.companies'), v: '36' },
                { l: t('designPreview.statCards.avgTaxonomy'), v: '20.8%' },
                { l: t('designPreview.statCards.avgRenewable'), v: '50.5%' },
                { l: t('designPreview.kpis.years'), v: '3' },
              ].map((k, i) => (
                <div
                  key={i}
                  className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    {k.l}
                  </p>
                  <p className="mt-3 numeric-mono text-5xl font-semibold text-slate-900">{k.v}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Section>

      <Section
        id="banners"
        title={t('designPreview.sections.banners.title')}
        subtitle={t('designPreview.sections.banners.subtitle')}
      >
        <div className="space-y-3">
          <NoticeBanner tone="info" title={t('designPreview.banners.infoTitle')}>
            {t('designPreview.banners.infoBody')}
          </NoticeBanner>
          <NoticeBanner tone="warning" title={t('designPreview.banners.warningTitle')}>
            {t('designPreview.banners.warningBody')}
          </NoticeBanner>
          <NoticeBanner tone="success" title={t('designPreview.banners.successTitle')}>
            {t('designPreview.banners.successBody')}
          </NoticeBanner>
          <NoticeBanner tone="mode" title={t('designPreview.banners.modeTitle')}>
            {t('designPreview.banners.modeBody')}
          </NoticeBanner>
        </div>
      </Section>

      <Section
        id="filter-bar"
        title={t('designPreview.sections.filterBar.title')}
        subtitle={t('designPreview.sections.filterBar.subtitle')}
      >
        <div className="space-y-10">
          <div>
            <VariantLabel label={t('designPreview.variants.filterBarA')} />
            <FilterBar>
              <FilterBar.Field label={t('designPreview.filters.industry')} htmlFor="demo-branch">
                <Select>
                  <SelectTrigger id="demo-branch" className="h-11 bg-white">
                    <SelectValue placeholder={t('designPreview.filters.industryPlaceholder')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="d3511">{t('designPreview.filters.industryOption')}</SelectItem>
                  </SelectContent>
                </Select>
              </FilterBar.Field>
              <FilterBar.Field label={t('designPreview.filters.year')} htmlFor="demo-year">
                <Select>
                  <SelectTrigger id="demo-year" className="h-11 bg-white">
                    <SelectValue placeholder="2024" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="2024">2024</SelectItem>
                    <SelectItem value="2023">2023</SelectItem>
                  </SelectContent>
                </Select>
              </FilterBar.Field>
              <FilterBar.Actions>
                <Button>{t('designPreview.actions.recalculateBenchmarks')}</Button>
              </FilterBar.Actions>
            </FilterBar>
          </div>

          <div>
            <VariantLabel label={t('designPreview.variants.filterBarB')} />
            <FilterBar>
              <FilterBar.Field label={t('designPreview.filters.search')} htmlFor="demo-search">
                <Input
                  id="demo-search"
                  className="h-11 bg-white"
                  placeholder={t('designPreview.filters.searchPlaceholder')}
                />
              </FilterBar.Field>
              <FilterBar.Actions>
                <Button variant="outline" size="sm">{t('designPreview.actions.sortByName')}</Button>
                <Button variant="outline" size="sm">{t('designPreview.actions.sortByYear')}</Button>
                <Button variant="outline" size="sm">{t('designPreview.actions.csv')}</Button>
                <Button variant="outline" size="sm">{t('designPreview.actions.json')}</Button>
              </FilterBar.Actions>
            </FilterBar>
          </div>
        </div>
      </Section>

      <Section
        id="companies-mock"
        title={t('designPreview.sections.companiesMock.title')}
        subtitle={t('designPreview.sections.companiesMock.subtitle')}
      >
        <div className="space-y-8">
          <PageHeader
            title={t('designPreview.samples.companiesTitle')}
            subtitle={t('designPreview.samples.companiesSubtitle')}
            kpis={[
              { label: t('designPreview.kpis.companies'), value: '36' },
              { label: t('designPreview.kpis.years'), value: '3' },
              { label: t('designPreview.kpis.datasets'), value: '36' },
            ]}
          />

          <FilterBar>
            <FilterBar.Field label={t('designPreview.filters.search')} htmlFor="mock-search">
              <Input
                id="mock-search"
                className="h-11 bg-white"
                placeholder={t('designPreview.filters.searchPlaceholder')}
              />
            </FilterBar.Field>
            <FilterBar.Actions>
              <Button variant="outline" size="sm">{t('designPreview.actions.sortByName')}</Button>
              <Button variant="outline" size="sm">{t('designPreview.actions.sortByYear')}</Button>
              <Button variant="outline" size="sm">{t('designPreview.actions.sortByTaxonomy')}</Button>
              <Button variant="outline" size="sm">{t('designPreview.actions.csv')}</Button>
              <Button variant="outline" size="sm">{t('designPreview.actions.json')}</Button>
            </FilterBar.Actions>
          </FilterBar>

          <NoticeBanner tone="info">
            {t('designPreview.companiesMock.trendBanner')}
          </NoticeBanner>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[
              { name: 'BASF SE', scope1: '15.552.000', emp: '111.831', tax: '—' },
              { name: 'BMW AG', scope1: '672.542', emp: '159.104', tax: '17.2%' },
              { name: 'Deutsche Telekom AG', scope1: '289.440', emp: '198.100', tax: '—' },
            ].map((c) => (
              <Panel
                key={c.name}
                title={c.name}
                description={t('designPreview.companiesMock.cardDescription')}
              >
                <dl className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <dt className="text-[11px] uppercase tracking-[0.14em] text-slate-500">
                      {t('designPreview.companiesMock.scope1')}
                    </dt>
                    <dd className="mt-1 numeric-mono font-semibold text-slate-900">{c.scope1}</dd>
                    <dd className="text-xs text-slate-500">tCO₂e</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] uppercase tracking-[0.14em] text-slate-500">
                      {t('designPreview.companiesMock.employeesShort')}
                    </dt>
                    <dd className="mt-1 numeric-mono font-semibold text-slate-900">{c.emp}</dd>
                    <dd className="text-xs text-slate-500">{t('designPreview.companiesMock.people')}</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] uppercase tracking-[0.14em] text-slate-500">
                      {t('designPreview.companiesMock.taxonomy')}
                    </dt>
                    <dd className="mt-1 numeric-mono font-semibold text-slate-900">{c.tax}</dd>
                    <dd className="text-xs text-slate-500">{t('designPreview.companiesMock.revenuePercent')}</dd>
                  </div>
                </dl>
              </Panel>
            ))}
          </div>
        </div>
      </Section>

      <div className="rounded-3xl border-2 border-amber-300 bg-amber-50 p-6">
        <h2 className="text-xl font-semibold text-amber-900">{t('designPreview.footer.title')}</h2>
        <p className="mt-2 text-sm text-amber-800">
          {t('designPreview.footer.body')}
        </p>
        <ul className="mt-3 space-y-1 text-sm text-amber-900">
          <li>{t('designPreview.footer.bulletHeader')}</li>
          <li>{t('designPreview.footer.bulletStatCards')}</li>
          <li>{t('designPreview.footer.bulletFilterBar')}</li>
          <li>{t('designPreview.footer.bulletBanners')}</li>
        </ul>
      </div>
    </PageContainer>
  )
}
