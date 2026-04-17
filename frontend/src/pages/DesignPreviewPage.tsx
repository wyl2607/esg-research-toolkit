/**
 * /design-preview — dev-only page for comparing new design system primitives.
 * Route registered in App.tsx. Not linked from Sidebar — access via URL.
 *
 * User opens http://localhost:5173/design-preview, scrolls, picks which
 * variant they want, and tells Claude. Claude then applies the chosen
 * variant as the locked default for Phase 2 page migration.
 */
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

function Section({ id, title, subtitle, children }: { id: string; title: string; subtitle?: string; children: React.ReactNode }) {
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
  return (
    <PageContainer>
      <div className="rounded-3xl bg-gradient-to-br from-amber-50 to-stone-50 p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">
          Internal · Design Preview
        </p>
        <h1 className="mt-2 text-4xl font-semibold text-slate-900">
          Design System — pick your variants
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Scroll through each section and tell Claude which variant (A / B / C) should lock in.
          The chosen set becomes the baseline for Phase 2 page migration.
        </p>
        <nav className="mt-5 flex flex-wrap gap-2">
          {['header', 'stat-cards', 'banners', 'filter-bar', 'companies-mock'].map((id) => (
            <a
              key={id}
              href={`#${id}`}
              className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:border-amber-500 hover:text-amber-800"
            >
              {id}
            </a>
          ))}
        </nav>
      </div>

      {/* ──────────────────── Section 1: PageHeader ──────────────────── */}
      <Section
        id="header"
        title="Page header — 3 variants"
        subtitle="Decide: kicker? KPIs? actions right or below?"
      >
        <div className="space-y-10">
          <div>
            <VariantLabel label="A · clean (recommended)" />
            <PageHeader
              title="Unternehmen"
              subtitle="Gespeicherte Unternehmensfälle als wiederverwendbare Analyseobjekte lesen."
              actions={<Button variant="outline">CSV exportieren</Button>}
              kpis={[
                { label: 'Unternehmen', value: '36' },
                { label: 'Jahre', value: '3' },
                { label: 'Datensätze', value: '36' },
              ]}
            />
          </div>

          <div>
            <VariantLabel label="B · with kicker" />
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-amber-700">
                Unternehmensintelligenz
              </p>
              <PageHeader
                title="Unternehmen"
                subtitle="Gespeicherte Unternehmensfälle als wiederverwendbare Analyseobjekte lesen."
                kpis={[
                  { label: 'Unternehmen', value: '36' },
                  { label: 'Jahre', value: '3' },
                  { label: 'Datensätze', value: '36' },
                ]}
              />
            </div>
          </div>

          <div>
            <VariantLabel label="C · no KPIs, just title + actions" />
            <PageHeader
              title="Unternehmensvergleich"
              subtitle="Mehrere Unternehmensfälle nebeneinander legen."
              actions={
                <div className="flex gap-2">
                  <Button variant="outline">Reset</Button>
                  <Button>Vergleich starten</Button>
                </div>
              }
            />
          </div>
        </div>
      </Section>

      {/* ──────────────────── Section 2: StatCard ──────────────────── */}
      <Section
        id="stat-cards"
        title="Stat cards — 2 densities"
        subtitle="Same component, decide the default size"
      >
        <div className="space-y-10">
          <div>
            <VariantLabel label="A · compact (p-4, text-3xl) — recommended" />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatCard label="Unternehmen" value="36" />
              <StatCard label="Ø Taxonomie" value="20.8%" />
              <StatCard label="Ø Erneuerbare" value="50.5%" />
              <StatCard label="Jahre" value="3" hint="2022–2024" />
            </div>
          </div>

          <div>
            <VariantLabel label="B · spacious (p-6, text-5xl) — Dashboard current" />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                { l: 'Unternehmen', v: '36' },
                { l: 'Ø Taxonomie', v: '20.8%' },
                { l: 'Ø Erneuerbare', v: '50.5%' },
                { l: 'Jahre', v: '3' },
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

      {/* ──────────────────── Section 3: NoticeBanner ──────────────────── */}
      <Section
        id="banners"
        title="Notice banners — 4 semantic tones"
        subtitle="Replaces the 5 different banner colors currently in use"
      >
        <div className="space-y-3">
          <NoticeBanner tone="info" title="Hinweis">
            Diese Ansicht spiegelt wider, was das Unternehmen im Rahmen der EU-Taxonomie offengelegt hat.
          </NoticeBanner>
          <NoticeBanner tone="warning" title="Kleine Stichprobe">
            Die aktuelle Auswahl enthält Stichprobengrößen bis hinunter zu 1. Mit Vorsicht interpretieren.
          </NoticeBanner>
          <NoticeBanner tone="success" title="Kernaussage">
            Der Anteil erneuerbarer Energien stieg um +6,0%, während Scope 1 Emissionen um 10.000 t zurückgingen.
          </NoticeBanner>
          <NoticeBanner tone="mode" title="Projektanalyse-Modus">
            Eingaben sind vom Benutzer bereitgestellte technische Parameter.
          </NoticeBanner>
        </div>
      </Section>

      {/* ──────────────────── Section 4: FilterBar ──────────────────── */}
      <Section
        id="filter-bar"
        title="Filter bar"
        subtitle="Unified pattern for selector + action rows"
      >
        <div className="space-y-10">
          <div>
            <VariantLabel label="A · fields + primary action" />
            <FilterBar>
              <FilterBar.Field label="Branche" htmlFor="demo-branch">
                <Select>
                  <SelectTrigger id="demo-branch" className="h-11 bg-white">
                    <SelectValue placeholder="Elektrizitätserzeugung" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="d3511">D35.11 — Elektrizitätserzeugung</SelectItem>
                  </SelectContent>
                </Select>
              </FilterBar.Field>
              <FilterBar.Field label="Jahr" htmlFor="demo-year">
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
                <Button>Benchmarks neu berechnen</Button>
              </FilterBar.Actions>
            </FilterBar>
          </div>

          <div>
            <VariantLabel label="B · search + sort chips + export cluster" />
            <FilterBar>
              <FilterBar.Field label="Suche" htmlFor="demo-search">
                <Input id="demo-search" className="h-11 bg-white" placeholder="Unternehmen suchen…" />
              </FilterBar.Field>
              <FilterBar.Actions>
                <Button variant="outline" size="sm">Nach Name</Button>
                <Button variant="outline" size="sm">Nach Jahr</Button>
                <Button variant="outline" size="sm">CSV</Button>
                <Button variant="outline" size="sm">JSON</Button>
              </FilterBar.Actions>
            </FilterBar>
          </div>
        </div>
      </Section>

      {/* ──────────────────── Section 5: Full Companies mock ──────────────────── */}
      <Section
        id="companies-mock"
        title="Full Companies page — new look (mock)"
        subtitle="All 6 primitives composed into one page. This is what Phase 2 delivers."
      >
        <div className="space-y-8">
          <PageHeader
            title="Unternehmen"
            subtitle="Gespeicherte Unternehmensfälle als wiederverwendbare Analyseobjekte lesen."
            kpis={[
              { label: 'Unternehmen', value: '36' },
              { label: 'Jahre', value: '3' },
              { label: 'Datensätze', value: '36' },
            ]}
          />

          <FilterBar>
            <FilterBar.Field label="Suche" htmlFor="mock-search">
              <Input id="mock-search" className="h-11 bg-white" placeholder="Unternehmen suchen…" />
            </FilterBar.Field>
            <FilterBar.Actions>
              <Button variant="outline" size="sm">Nach Name</Button>
              <Button variant="outline" size="sm">Nach Jahr</Button>
              <Button variant="outline" size="sm">Nach Taxonomie</Button>
              <Button variant="outline" size="sm">CSV</Button>
              <Button variant="outline" size="sm">JSON</Button>
            </FilterBar.Actions>
          </FilterBar>

          <NoticeBanner tone="info">
            3 von 36 Unternehmen haben Trenddaten für 2022–2024. Der Rest nur 2024.
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
                description="sustainability_report · 2024"
              >
                <dl className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <dt className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Scope 1</dt>
                    <dd className="mt-1 numeric-mono font-semibold text-slate-900">{c.scope1}</dd>
                    <dd className="text-xs text-slate-500">tCO₂e</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Mitarb.</dt>
                    <dd className="mt-1 numeric-mono font-semibold text-slate-900">{c.emp}</dd>
                    <dd className="text-xs text-slate-500">Personen</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Taxonomie</dt>
                    <dd className="mt-1 numeric-mono font-semibold text-slate-900">{c.tax}</dd>
                    <dd className="text-xs text-slate-500">% Umsatz</dd>
                  </div>
                </dl>
              </Panel>
            ))}
          </div>
        </div>
      </Section>

      {/* ──────────────────── Decision cheatsheet ──────────────────── */}
      <div className="rounded-3xl border-2 border-amber-300 bg-amber-50 p-6">
        <h2 className="text-xl font-semibold text-amber-900">Decision cheatsheet</h2>
        <p className="mt-2 text-sm text-amber-800">
          Tell Claude: "Header = A, StatCard = A, FilterBar A+B, Companies mock looks good" — he will lock these and hand over the Codex migration script for Phase 2.
        </p>
        <ul className="mt-3 space-y-1 text-sm text-amber-900">
          <li>• Header · <strong>A</strong> (clean) / <strong>B</strong> (kicker) / <strong>C</strong> (no KPIs)</li>
          <li>• StatCard · <strong>A</strong> (compact) / <strong>B</strong> (spacious)</li>
          <li>• FilterBar — use both <strong>A</strong> and <strong>B</strong> (different page types)</li>
          <li>• Banners — keep all 4 tones, they're semantic</li>
        </ul>
      </div>
    </PageContainer>
  )
}
