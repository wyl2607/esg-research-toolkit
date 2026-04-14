import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowRight, CheckCircle2, Layers3, Palette, Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'

type StyleOption = {
  id: string
  accent: string
  surface: string
  panel: string
  chip: string
  text: string
}

const STYLE_OPTIONS: StyleOption[] = [
  {
    id: 'analyst_blue',
    accent: 'bg-sky-700',
    surface: 'bg-slate-950',
    panel: 'bg-white',
    chip: 'bg-sky-50 text-sky-800 border-sky-200',
    text: 'text-slate-900',
  },
  {
    id: 'dense_graphite',
    accent: 'bg-emerald-500',
    surface: 'bg-slate-900',
    panel: 'bg-slate-800',
    chip: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    text: 'text-white',
  },
  {
    id: 'editorial_warm',
    accent: 'bg-amber-600',
    surface: 'bg-stone-100',
    panel: 'bg-white',
    chip: 'bg-amber-50 text-amber-800 border-amber-200',
    text: 'text-stone-900',
  },
]

export function DesignLabPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <p className="section-kicker">{t('designLab.kicker')}</p>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold text-slate-900">{t('designLab.title')}</h1>
            <p className="max-w-4xl text-sm leading-6 text-slate-600">{t('designLab.subtitle')}</p>
          </div>
          <Badge variant="outline" className="w-fit rounded-full border-slate-300 bg-white/80 px-3 py-1 text-slate-600">
            <Palette size={13} className="mr-1.5" />
            {t('designLab.badge')}
          </Badge>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        {STYLE_OPTIONS.map((style, index) => {
          const recommended = style.id === 'analyst_blue'
          return (
            <Card key={style.id} className="surface-card overflow-hidden">
              <div className={`h-2 w-full ${style.accent}`} />
              <CardHeader className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle className="text-xl">{t(`designLab.styles.${style.id}.name`)}</CardTitle>
                    <p className="text-sm leading-6 text-slate-600">
                      {t(`designLab.styles.${style.id}.summary`)}
                    </p>
                  </div>
                  {recommended ? (
                    <Badge className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-sky-800">
                      <Sparkles size={12} className="mr-1.5" />
                      {t('designLab.recommended')}
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="rounded-full">
                      {String(index + 1).padStart(2, '0')}
                    </Badge>
                  )}
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className={`rounded-full border px-2.5 py-1 ${style.chip}`}>
                    {t(`designLab.styles.${style.id}.tone`)}
                  </span>
                  <span className={`rounded-full border px-2.5 py-1 ${style.chip}`}>
                    {t(`designLab.styles.${style.id}.fit`)}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className={`rounded-3xl border border-slate-200/60 p-4 ${style.surface}`}>
                  <div className={`rounded-2xl border border-white/10 p-4 ${style.panel}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                          {t('designLab.mock.kicker')}
                        </p>
                        <h3 className={`max-w-xs text-xl font-semibold leading-tight ${style.text}`}>
                          {t('designLab.mock.company')}
                        </h3>
                        <p className="text-xs leading-5 text-slate-500">{t('designLab.mock.subhead')}</p>
                      </div>
                      <div className={`rounded-full px-3 py-1 text-[11px] font-medium ${style.chip}`}>
                        FY2025
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      <div className="rounded-2xl border border-slate-200/60 bg-white/80 p-3">
                        <p className="section-kicker">{t('designLab.mock.metric1')}</p>
                        <p className="mt-2 numeric-mono text-lg font-semibold text-slate-900">93,440</p>
                        <p className="mt-1 text-[11px] text-slate-500">tCO2e</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200/60 bg-white/80 p-3">
                        <p className="section-kicker">{t('designLab.mock.metric2')}</p>
                        <p className="mt-2 numeric-mono text-lg font-semibold text-slate-900">24.7</p>
                        <p className="mt-1 text-[11px] text-slate-500">%</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200/60 bg-white/80 p-3">
                        <p className="section-kicker">{t('designLab.mock.metric3')}</p>
                        <p className="mt-2 numeric-mono text-lg font-semibold text-slate-900">usable</p>
                        <p className="mt-1 text-[11px] text-slate-500">{t('designLab.mock.readiness')}</p>
                      </div>
                    </div>

                    <div className="mt-4 space-y-2 rounded-2xl border border-slate-200/60 bg-slate-50/80 p-3">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                          <Layers3 size={14} className="text-slate-500" />
                          {t('designLab.mock.identity')}
                        </div>
                        <CheckCircle2 size={14} className="text-emerald-600" />
                      </div>
                      <p className="text-xs leading-5 text-slate-500">
                        {t(`designLab.styles.${style.id}.behavior`)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    {t('designLab.whatChanges')}
                  </p>
                  <ul className="space-y-2 text-sm leading-6 text-slate-700">
                    <li>{t(`designLab.styles.${style.id}.change1`)}</li>
                    <li>{t(`designLab.styles.${style.id}.change2`)}</li>
                    <li>{t(`designLab.styles.${style.id}.change3`)}</li>
                  </ul>
                </div>

                <Button variant={recommended ? 'default' : 'outline'} className="w-full rounded-xl justify-between">
                  {t('designLab.chooseThis')}
                  <ArrowRight size={14} />
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card className="surface-card">
        <CardContent className="space-y-3 p-6">
          <p className="section-kicker">{t('designLab.myRecommendation')}</p>
          <h2 className="text-xl font-semibold text-slate-900">{t('designLab.recommendationTitle')}</h2>
          <p className="max-w-4xl text-sm leading-6 text-slate-600">{t('designLab.recommendationBody')}</p>
        </CardContent>
      </Card>
    </div>
  )
}
