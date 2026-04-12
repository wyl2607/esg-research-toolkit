# Task 18: 前端完整三语言支持（EN / ZH / DE）

**目标**:
- 安装 react-i18next，所有 UI 文本（页面、组件、错误/警告/提示）全部可切换语言
- 支持：English / 中文 / Deutsch
- 语言切换按钮放在顶部 Header，选择后立即生效并持久化（localStorage）
- 覆盖范围：7 个页面 + Sidebar + 所有 alert/toast/error/loading 状态文案

**优先级**: P1

**预计时间**: 2–3 小时（Codex loop 自动执行）

---

## 自愈策略

每步完成后运行验证点。失败重试最多 3 次，仍失败记录后继续。

---

## Step 1 — 安装依赖

```bash
cd frontend
npm install i18next react-i18next i18next-browser-languagedetector
npm install --save-dev @types/i18next
```

**验证点**:
```bash
node -e "require('./node_modules/react-i18next')" && echo "✓ react-i18next installed"
```

---

## Step 2 — 创建翻译文件

创建目录和三份翻译 JSON：

```bash
mkdir -p frontend/src/i18n/locales
```

### 2-A `frontend/src/i18n/locales/en.json`

写入以下完整 JSON（所有 key 必须完整，不能遗漏）：

```json
{
  "nav": {
    "dashboard": "Dashboard",
    "upload": "Upload",
    "taxonomy": "Taxonomy",
    "lcoe": "LCOE",
    "companies": "Companies",
    "compare": "Compare",
    "frameworks": "Frameworks",
    "appName": "ESG Toolkit"
  },
  "common": {
    "loading": "Loading…",
    "error": "Error",
    "noData": "No data available",
    "selectCompany": "Select company & year…",
    "company": "Company",
    "year": "Year",
    "score": "Score",
    "gaps": "Gaps",
    "recommendations": "Recommendations",
    "save": "Save",
    "delete": "Delete",
    "cancel": "Cancel",
    "confirm": "Confirm",
    "search": "Search",
    "export": "Export",
    "download": "Download",
    "missing": "Missing",
    "coverage": "Coverage",
    "grade": "Grade",
    "summary": "Summary"
  },
  "dashboard": {
    "title": "Dashboard",
    "companiesAnalyzed": "Companies Analyzed",
    "avgTaxonomy": "Avg Taxonomy Alignment",
    "reportsWithData": "Reports with Taxonomy Data",
    "recentAnalyses": "Recent Analyses",
    "keyMetrics": "Key Metrics",
    "noCompanies": "No companies yet. Upload a PDF report to get started.",
    "runTaxonomy": "Run Taxonomy Score →",
    "uploadReport": "Upload Report"
  },
  "upload": {
    "title": "Upload ESG Report",
    "dropzone": "Drop the PDF file(s) here…",
    "dropzoneHint": "or click to select files",
    "singleUpload": "Single Upload",
    "batchUpload": "Batch Upload",
    "uploading": "Uploading…",
    "processing": "Processing…",
    "success": "Extraction successful",
    "error": "Upload failed",
    "aiError": "AI extraction failed — please check your API configuration",
    "pdfError": "Could not extract text from this PDF. Please ensure it is not a scanned image.",
    "batchProgress": "Batch Analysis Progress",
    "completed": "Completed",
    "failed": "Failed",
    "queued": "Queued",
    "viewTaxonomy": "View Taxonomy →",
    "renewableEnergy": "Renewable Energy",
    "taxonomyAligned": "Taxonomy Aligned Revenue"
  },
  "taxonomy": {
    "title": "Taxonomy Scoring",
    "downloadPdf": "Download PDF",
    "generating": "Generating…",
    "revenueAligned": "Revenue Aligned",
    "capexAligned": "CapEx Aligned",
    "opexAligned": "OpEx Aligned",
    "dnshStatus": "DNSH Status",
    "dnshPass": "✓ Pass",
    "dnshFail": "✗ Fail",
    "dnshAllMet": "All DNSH criteria met",
    "dnshNotMet": "DNSH criteria not fully met",
    "objectiveScores": "Objective Scores",
    "dnshCheck": "DNSH Check",
    "loadingData": "Loading taxonomy data…",
    "selectPrompt": "Select a company above to view taxonomy analysis."
  },
  "lcoe": {
    "title": "LCOE Analysis",
    "technology": "Technology",
    "calculate": "Calculate",
    "calculating": "Calculating…",
    "loadBenchmark": "Load Benchmark",
    "lcoe": "LCOE",
    "npv": "NPV",
    "irr": "IRR",
    "payback": "Payback",
    "years": "yr",
    "sensitivityAnalysis": "Sensitivity Analysis",
    "capex": "CapEx (€/kW)",
    "opex": "OpEx (€/kW/yr)",
    "capacityFactor": "Capacity Factor",
    "lifetime": "Lifetime (years)",
    "discountRate": "Discount Rate"
  },
  "companies": {
    "title": "Companies",
    "searchPlaceholder": "Search companies…",
    "noResults": "No companies found.",
    "deleteConfirm": "Delete {{name}} ({{year}})?",
    "deleteSuccess": "Company deleted",
    "deleteError": "Failed to delete company",
    "csvExport": "CSV",
    "excelExport": "Excel",
    "scope1": "Scope 1 (tCO₂e)",
    "scope2": "Scope 2 (tCO₂e)",
    "renewable": "Renewable %",
    "employees": "Employees"
  },
  "compare": {
    "title": "Compare Companies",
    "selectUp4": "Select up to 4 companies to compare",
    "revenueAligned": "Revenue Aligned",
    "renewable": "Renewable Energy",
    "femalePct": "Female Employees",
    "noSelection": "Select companies above to compare metrics."
  },
  "frameworks": {
    "title": "Multi-Framework ESG",
    "subtitle": "Compare EU Taxonomy 2020 · China CSRC 2023 · EU CSRD/ESRS simultaneously",
    "selectPrompt": "Select a company to view tri-framework scoring and gap analysis.",
    "calculating": "Calculating scores for all three frameworks…",
    "totalScore": "Overall Score",
    "coverage": "Coverage {{pct}}%",
    "viewGaps": "View gaps ({{count}}) and recommendations ({{recs}})",
    "collapse": "Collapse",
    "disclosed": "{{n}}/{{total}} disclosed"
  },
  "errors": {
    "networkError": "Network error — please check your connection",
    "serverError": "Server error ({{status}}) — please try again",
    "notFound": "Not found",
    "unauthorized": "API key invalid or not configured",
    "rateLimited": "Rate limit exceeded — please retry in a moment",
    "timeout": "Request timed out",
    "unknown": "An unexpected error occurred"
  },
  "language": {
    "label": "Language",
    "en": "English",
    "zh": "中文",
    "de": "Deutsch"
  }
}
```

### 2-B `frontend/src/i18n/locales/zh.json`

写入完整中文翻译：

```json
{
  "nav": {
    "dashboard": "仪表盘",
    "upload": "上传",
    "taxonomy": "分类法评分",
    "lcoe": "度电成本",
    "companies": "公司列表",
    "compare": "对比分析",
    "frameworks": "多框架",
    "appName": "ESG 工具包"
  },
  "common": {
    "loading": "加载中…",
    "error": "错误",
    "noData": "暂无数据",
    "selectCompany": "选择公司和年份…",
    "company": "公司",
    "year": "年份",
    "score": "得分",
    "gaps": "差距",
    "recommendations": "建议",
    "save": "保存",
    "delete": "删除",
    "cancel": "取消",
    "confirm": "确认",
    "search": "搜索",
    "export": "导出",
    "download": "下载",
    "missing": "缺失",
    "coverage": "覆盖率",
    "grade": "评级",
    "summary": "摘要"
  },
  "dashboard": {
    "title": "仪表盘",
    "companiesAnalyzed": "已分析公司数",
    "avgTaxonomy": "平均分类法对齐率",
    "reportsWithData": "含分类法数据的报告",
    "recentAnalyses": "最近分析",
    "keyMetrics": "关键指标",
    "noCompanies": "暂无公司。请上传 PDF 报告开始分析。",
    "runTaxonomy": "进行分类法评分 →",
    "uploadReport": "上传报告"
  },
  "upload": {
    "title": "上传 ESG 报告",
    "dropzone": "将 PDF 文件拖拽至此…",
    "dropzoneHint": "或点击选择文件",
    "singleUpload": "单文件上传",
    "batchUpload": "批量上传",
    "uploading": "上传中…",
    "processing": "处理中…",
    "success": "提取成功",
    "error": "上传失败",
    "aiError": "AI 提取失败——请检查 API 配置",
    "pdfError": "无法从此 PDF 提取文本，请确认非扫描图片版本。",
    "batchProgress": "批量分析进度",
    "completed": "已完成",
    "failed": "失败",
    "queued": "排队中",
    "viewTaxonomy": "查看分类法评分 →",
    "renewableEnergy": "可再生能源比例",
    "taxonomyAligned": "分类法对齐收入"
  },
  "taxonomy": {
    "title": "EU 分类法评分",
    "downloadPdf": "下载 PDF",
    "generating": "生成中…",
    "revenueAligned": "收入对齐率",
    "capexAligned": "资本支出对齐率",
    "opexAligned": "运营支出对齐率",
    "dnshStatus": "DNSH 状态",
    "dnshPass": "✓ 通过",
    "dnshFail": "✗ 未通过",
    "dnshAllMet": "所有 DNSH 标准均已满足",
    "dnshNotMet": "DNSH 标准未完全满足",
    "objectiveScores": "六大目标得分",
    "dnshCheck": "DNSH 检查",
    "loadingData": "正在加载分类法数据…",
    "selectPrompt": "请在上方选择公司以查看分析结果。"
  },
  "lcoe": {
    "title": "度电成本分析",
    "technology": "技术类型",
    "calculate": "计算",
    "calculating": "计算中…",
    "loadBenchmark": "加载基准参数",
    "lcoe": "度电成本",
    "npv": "净现值",
    "irr": "内部收益率",
    "payback": "回收期",
    "years": "年",
    "sensitivityAnalysis": "敏感性分析",
    "capex": "资本支出（€/kW）",
    "opex": "运营成本（€/kW/年）",
    "capacityFactor": "容量因子",
    "lifetime": "使用寿命（年）",
    "discountRate": "折现率"
  },
  "companies": {
    "title": "公司列表",
    "searchPlaceholder": "搜索公司…",
    "noResults": "未找到公司。",
    "deleteConfirm": "确认删除 {{name}}（{{year}}）？",
    "deleteSuccess": "公司已删除",
    "deleteError": "删除失败",
    "csvExport": "CSV",
    "excelExport": "Excel",
    "scope1": "范围一排放（tCO₂e）",
    "scope2": "范围二排放（tCO₂e）",
    "renewable": "可再生能源 %",
    "employees": "员工人数"
  },
  "compare": {
    "title": "公司对比",
    "selectUp4": "最多选择 4 家公司进行对比",
    "revenueAligned": "收入对齐率",
    "renewable": "可再生能源",
    "femalePct": "女性员工比例",
    "noSelection": "请在上方选择公司以比较指标。"
  },
  "frameworks": {
    "title": "多框架 ESG 评分",
    "subtitle": "同时对比 EU Taxonomy 2020 · 中国证监会 CSRC 2023 · EU CSRD/ESRS",
    "selectPrompt": "选择一家公司，查看三大框架评分与差距分析。",
    "calculating": "正在计算三框架得分…",
    "totalScore": "综合得分",
    "coverage": "覆盖率 {{pct}}%",
    "viewGaps": "查看差距（{{count}}）和建议（{{recs}}）",
    "collapse": "收起",
    "disclosed": "{{n}}/{{total}} 项已披露"
  },
  "errors": {
    "networkError": "网络错误——请检查网络连接",
    "serverError": "服务器错误（{{status}}）——请稍后重试",
    "notFound": "未找到",
    "unauthorized": "API Key 无效或未配置",
    "rateLimited": "请求频率超限——请稍后重试",
    "timeout": "请求超时",
    "unknown": "发生未知错误"
  },
  "language": {
    "label": "语言",
    "en": "English",
    "zh": "中文",
    "de": "Deutsch"
  }
}
```

### 2-C `frontend/src/i18n/locales/de.json`

写入完整德文翻译（Sie-Form，正式风格）：

```json
{
  "nav": {
    "dashboard": "Dashboard",
    "upload": "Hochladen",
    "taxonomy": "Taxonomie",
    "lcoe": "Stromgestehungskosten",
    "companies": "Unternehmen",
    "compare": "Vergleich",
    "frameworks": "Rahmenwerke",
    "appName": "ESG Toolkit"
  },
  "common": {
    "loading": "Wird geladen…",
    "error": "Fehler",
    "noData": "Keine Daten verfügbar",
    "selectCompany": "Unternehmen & Jahr auswählen…",
    "company": "Unternehmen",
    "year": "Jahr",
    "score": "Bewertung",
    "gaps": "Lücken",
    "recommendations": "Empfehlungen",
    "save": "Speichern",
    "delete": "Löschen",
    "cancel": "Abbrechen",
    "confirm": "Bestätigen",
    "search": "Suchen",
    "export": "Exportieren",
    "download": "Herunterladen",
    "missing": "Fehlend",
    "coverage": "Abdeckung",
    "grade": "Bewertung",
    "summary": "Zusammenfassung"
  },
  "dashboard": {
    "title": "Dashboard",
    "companiesAnalyzed": "Analysierte Unternehmen",
    "avgTaxonomy": "Ø Taxonomie-Ausrichtung",
    "reportsWithData": "Berichte mit Taxonomiedaten",
    "recentAnalyses": "Letzte Analysen",
    "keyMetrics": "Kennzahlen",
    "noCompanies": "Noch keine Unternehmen. Laden Sie einen PDF-Bericht hoch.",
    "runTaxonomy": "Taxonomie-Bewertung starten →",
    "uploadReport": "Bericht hochladen"
  },
  "upload": {
    "title": "ESG-Bericht hochladen",
    "dropzone": "PDF-Dateien hier ablegen…",
    "dropzoneHint": "oder klicken Sie zur Dateiauswahl",
    "singleUpload": "Einzelupload",
    "batchUpload": "Stapelverarbeitung",
    "uploading": "Wird hochgeladen…",
    "processing": "Wird verarbeitet…",
    "success": "Extraktion erfolgreich",
    "error": "Upload fehlgeschlagen",
    "aiError": "KI-Extraktion fehlgeschlagen — bitte API-Konfiguration prüfen",
    "pdfError": "Text konnte nicht extrahiert werden. Bitte prüfen Sie, ob es sich um ein gescanntes Dokument handelt.",
    "batchProgress": "Stapelverarbeitungs-Fortschritt",
    "completed": "Abgeschlossen",
    "failed": "Fehlgeschlagen",
    "queued": "In Warteschlange",
    "viewTaxonomy": "Taxonomie-Auswertung →",
    "renewableEnergy": "Erneuerbare Energien",
    "taxonomyAligned": "Taxonomiekonforme Einnahmen"
  },
  "taxonomy": {
    "title": "Taxonomie-Bewertung",
    "downloadPdf": "PDF herunterladen",
    "generating": "Wird erstellt…",
    "revenueAligned": "Umsatzkonform",
    "capexAligned": "Investitionskonform",
    "opexAligned": "Betriebskonform",
    "dnshStatus": "DNSH-Status",
    "dnshPass": "✓ Bestanden",
    "dnshFail": "✗ Nicht bestanden",
    "dnshAllMet": "Alle DNSH-Kriterien erfüllt",
    "dnshNotMet": "DNSH-Kriterien nicht vollständig erfüllt",
    "objectiveScores": "Ziel-Bewertungen",
    "dnshCheck": "DNSH-Prüfung",
    "loadingData": "Taxonomiedaten werden geladen…",
    "selectPrompt": "Bitte wählen Sie oben ein Unternehmen aus."
  },
  "lcoe": {
    "title": "Stromgestehungskosten-Analyse",
    "technology": "Technologie",
    "calculate": "Berechnen",
    "calculating": "Wird berechnet…",
    "loadBenchmark": "Benchmark laden",
    "lcoe": "LCOE",
    "npv": "Kapitalwert",
    "irr": "Interner Zinsfuß",
    "payback": "Amortisationszeit",
    "years": "Jahre",
    "sensitivityAnalysis": "Sensitivitätsanalyse",
    "capex": "Investitionskosten (€/kW)",
    "opex": "Betriebskosten (€/kW/Jahr)",
    "capacityFactor": "Kapazitätsfaktor",
    "lifetime": "Lebensdauer (Jahre)",
    "discountRate": "Diskontierungssatz"
  },
  "companies": {
    "title": "Unternehmen",
    "searchPlaceholder": "Unternehmen suchen…",
    "noResults": "Keine Unternehmen gefunden.",
    "deleteConfirm": "{{name}} ({{year}}) wirklich löschen?",
    "deleteSuccess": "Unternehmen gelöscht",
    "deleteError": "Löschen fehlgeschlagen",
    "csvExport": "CSV",
    "excelExport": "Excel",
    "scope1": "Scope 1 (tCO₂e)",
    "scope2": "Scope 2 (tCO₂e)",
    "renewable": "Erneuerbare %",
    "employees": "Mitarbeiter"
  },
  "compare": {
    "title": "Unternehmensvergleich",
    "selectUp4": "Bis zu 4 Unternehmen zum Vergleich auswählen",
    "revenueAligned": "Taxonomiekonforme Einnahmen",
    "renewable": "Erneuerbare Energien",
    "femalePct": "Frauenanteil",
    "noSelection": "Bitte wählen Sie oben Unternehmen für den Vergleich."
  },
  "frameworks": {
    "title": "Multi-Rahmenwerk ESG",
    "subtitle": "EU-Taxonomie 2020 · China CSRC 2023 · EU CSRD/ESRS im Vergleich",
    "selectPrompt": "Wählen Sie ein Unternehmen für die Drei-Rahmenwerk-Analyse.",
    "calculating": "Bewertungen für alle drei Rahmenwerke werden berechnet…",
    "totalScore": "Gesamtbewertung",
    "coverage": "Abdeckung {{pct}}%",
    "viewGaps": "Lücken ({{count}}) und Empfehlungen ({{recs}}) anzeigen",
    "collapse": "Einklappen",
    "disclosed": "{{n}}/{{total}} offengelegt"
  },
  "errors": {
    "networkError": "Netzwerkfehler — bitte Verbindung prüfen",
    "serverError": "Serverfehler ({{status}}) — bitte erneut versuchen",
    "notFound": "Nicht gefunden",
    "unauthorized": "API-Schlüssel ungültig oder nicht konfiguriert",
    "rateLimited": "Anfragelimit überschritten — bitte kurz warten",
    "timeout": "Zeitüberschreitung der Anfrage",
    "unknown": "Ein unerwarteter Fehler ist aufgetreten"
  },
  "language": {
    "label": "Sprache",
    "en": "English",
    "zh": "中文",
    "de": "Deutsch"
  }
}
```

**验证点**:
```bash
python3 -c "
import json, os
for lang in ['en','zh','de']:
    d = json.load(open(f'frontend/src/i18n/locales/{lang}.json'))
    keys = set(k for section in d.values() for k in section.keys())
    print(f'{lang}: {len(d)} sections, sections={list(d.keys())}')
"
```

---

## Step 3 — i18n 初始化文件

创建 `frontend/src/i18n/index.ts`：

```typescript
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import zh from './locales/zh.json'
import de from './locales/de.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, zh: { translation: zh }, de: { translation: de } },
    fallbackLng: 'en',
    supportedLngs: ['en', 'zh', 'de'],
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
    interpolation: { escapeValue: false },
  })

export default i18n
```

在 `frontend/src/main.tsx` 顶部加入：

```typescript
import './i18n/index'
```

（加在所有其他 import 之后，ReactDOM.render 之前）

**验证点**:
```bash
grep "i18n" frontend/src/main.tsx && echo "✓ i18n imported"
```

---

## Step 4 — 语言切换组件

创建 `frontend/src/components/LanguageSwitcher.tsx`：

```typescript
import { useTranslation } from 'react-i18next'

const LANGS = [
  { code: 'en', flag: '🇬🇧', label: 'EN' },
  { code: 'zh', flag: '🇨🇳', label: '中' },
  { code: 'de', flag: '🇩🇪', label: 'DE' },
]

export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  return (
    <div className="flex items-center gap-1">
      {LANGS.map(({ code, flag, label }) => (
        <button
          key={code}
          onClick={() => i18n.changeLanguage(code)}
          className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
            i18n.language === code
              ? 'bg-indigo-600 text-white'
              : 'text-slate-500 hover:bg-slate-100'
          }`}
          title={code}
        >
          {flag} {label}
        </button>
      ))}
    </div>
  )
}
```

在 `frontend/src/components/Layout.tsx` 中加入顶部 Header 栏（在 `<main>` 之前）：

```typescript
import { LanguageSwitcher } from './LanguageSwitcher'

// Layout 改为：
export function Layout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-10 border-b bg-white flex items-center justify-end px-6 shrink-0">
          <LanguageSwitcher />
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
```

---

## Step 5 — 替换所有页面和组件中的硬编码字符串

对每个文件，在顶部加 `const { t } = useTranslation()`，然后用 `t('key')` 替换所有硬编码字符串。

### 5-A Sidebar.tsx

```typescript
import { useTranslation } from 'react-i18next'

// links 数组改为在组件内用 t() 动态生成：
export function Sidebar() {
  const { t } = useTranslation()
  const links = [
    { to: '/', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/upload', label: t('nav.upload'), icon: Upload },
    { to: '/taxonomy', label: t('nav.taxonomy'), icon: Tag },
    { to: '/lcoe', label: t('nav.lcoe'), icon: Zap },
    { to: '/companies', label: t('nav.companies'), icon: Building2 },
    { to: '/compare', label: t('nav.compare'), icon: GitCompare },
    { to: '/frameworks', label: t('nav.frameworks'), icon: Globe },
  ]
  // ... 其余不变，但 "ESG Toolkit" 改为 {t('nav.appName')}
}
```

### 5-B DashboardPage.tsx

替换：
- `"Companies Analyzed"` → `{t('dashboard.companiesAnalyzed')}`
- `"Avg Taxonomy Alignment"` → `{t('dashboard.avgTaxonomy')}`
- `"Reports with Taxonomy Data"` → `{t('dashboard.reportsWithData')}`
- `"Recent Analyses"` → `{t('dashboard.recentAnalyses')}`
- `"Key Metrics"` → `{t('dashboard.keyMetrics')}`
- `"Upload Report"` → `{t('dashboard.uploadReport')}`
- `"Run Taxonomy Score →"` → `{t('dashboard.runTaxonomy')}`
- 无数据提示 → `{t('dashboard.noCompanies')}`

### 5-C UploadPage.tsx

替换：
- `"Upload ESG Report"` → `{t('upload.title')}`
- `"Drop the PDF file(s) here…"` → `{t('upload.dropzone')}`
- `"Batch Analysis Progress"` → `{t('upload.batchProgress')}`
- `"Uploading…"` / `"Processing…"` → `{t('upload.uploading')}` / `{t('upload.processing')}`
- 所有状态 badge（completed/failed/queued）→ `{t('upload.completed')}` 等
- error.message 替换为：
  ```typescript
  const errMsg = error?.message?.includes('401') ? t('errors.unauthorized')
    : error?.message?.includes('422') ? t('upload.aiError')
    : t('upload.error')
  ```

### 5-D TaxonomyPage.tsx

替换：
- `"Taxonomy Scoring"` → `{t('taxonomy.title')}`
- `"Download PDF"` / `"Generating…"` → `{t('taxonomy.downloadPdf')}` / `{t('taxonomy.generating')}`
- `"Revenue Aligned"` → `{t('taxonomy.revenueAligned')}`
- `"CapEx Aligned"` → `{t('taxonomy.capexAligned')}`
- `"OpEx Aligned"` → `{t('taxonomy.opexAligned')}`
- `"DNSH Status"` → `{t('taxonomy.dnshStatus')}`
- `"✓ Pass"` / `"✗ Fail"` → `{t('taxonomy.dnshPass')}` / `{t('taxonomy.dnshFail')}`
- `"Loading taxonomy data…"` → `{t('taxonomy.loadingData')}`
- Select placeholder → `{t('common.selectCompany')}`

### 5-E LcoePage.tsx

替换所有标签：technology / calculate / LCOE / NPV / IRR / Payback / Sensitivity Analysis 等

### 5-F CompaniesPage.tsx

替换：
- `"Search companies…"` → `{t('companies.searchPlaceholder')}`
- `` `Delete ${c.company_name} (${c.report_year})?` `` → `{t('companies.deleteConfirm', { name: c.company_name, year: c.report_year })}`
- `"No companies found."` → `{t('companies.noResults')}`
- `"CSV"` / `"Excel"` → `{t('companies.csvExport')}` / `{t('companies.excelExport')}`

### 5-G ComparePage.tsx

替换所有标签文本。

### 5-H FrameworksPage.tsx

替换：
- `"Multi-Framework ESG"` → `{t('frameworks.title')}`
- 副标题 → `{t('frameworks.subtitle')}`
- `"选择公司和年份…"` → `{t('common.selectCompany')}`（统一用 common key）
- `"正在计算三框架得分…"` → `{t('frameworks.calculating')}`
- `"综合得分"` → `{t('frameworks.totalScore')}`
- `"覆盖率 X%"` → `{t('frameworks.coverage', { pct: fw.coverage_pct })}`
- `"查看差距 (N) 和建议 (M)"` → `{t('frameworks.viewGaps', { count: fw.gaps.length, recs: fw.recommendations.length })}`
- `"收起"` → `{t('frameworks.collapse')}`
- `"X/N 项"` → `{t('frameworks.disclosed', { n: d.disclosed, total: d.total })}`
- `"缺失"` badge → `{t('common.missing')}`

**验证点（每个文件替换后）**:
```bash
# 检查是否还有中文硬编码残留
grep -r "[\u4e00-\u9fff]" frontend/src/pages/ frontend/src/components/ --include="*.tsx" | grep -v "\.json\|i18n" | grep -v "//.*[\u4e00-\u9fff]"
# 预期：无输出（所有中文已移入 JSON）
```

---

## Step 6 — 构建验证

```bash
cd frontend
npm run build 2>&1 | tail -10
```

**验证点**:
```bash
# 构建无 TypeScript 错误
npm run build 2>&1 | grep -c "error TS" | xargs -I{} test {} -eq 0 && echo "✓ No TS errors"
```

---

## Step 7 — 运行时冒烟测试

```bash
# 启动开发服务器并截图（如有 playwright）
source ../.venv/bin/activate && uvicorn main:app --port 8000 &
cd frontend && npm run dev &
sleep 3
curl -sf http://localhost:5173/ | grep -o '<title>[^<]*' && echo "✓ Dev server running"
```

---

## Step 8 — Commit & Push

```bash
git add frontend/src/i18n/ \
        frontend/src/components/LanguageSwitcher.tsx \
        frontend/src/components/Layout.tsx \
        frontend/src/components/Sidebar.tsx \
        frontend/src/main.tsx \
        frontend/src/pages/ \
        frontend/package.json \
        frontend/package-lock.json
git commit -m "feat: full trilingual frontend i18n (EN/ZH/DE)

- Install react-i18next + i18next-browser-languagedetector
- Translation files: en.json / zh.json / de.json (9 sections, ~80 keys each)
- LanguageSwitcher component in header (flag + code buttons)
- Language persisted in localStorage, auto-detected from browser
- All pages, Sidebar, error messages, alerts, loading states translated
- Zero hardcoded UI strings remaining in .tsx files"
git push origin HEAD
```

---

## 完成标准

- [ ] `frontend/src/i18n/locales/en.json` 存在，9 个 section
- [ ] `frontend/src/i18n/locales/zh.json` 存在，9 个 section
- [ ] `frontend/src/i18n/locales/de.json` 存在，9 个 section
- [ ] `LanguageSwitcher.tsx` 存在，三语言切换按钮在 Header
- [ ] 所有 7 个页面均使用 `t()` 替代硬编码字符串
- [ ] `grep -r "[\u4e00-\u9fff]" frontend/src/pages/` 无 .tsx 文件输出
- [ ] `npm run build` 无 TypeScript 错误
- [ ] 已 commit push

---

## 执行指令（直接传给 Codex）

```
在 ~/projects/esg-research-toolkit 执行 docs/codex-tasks/task_18_frontend_i18n.md，使用自愈 loop 模式。

重点注意：
1. Step 2 的三份 JSON 必须完整写入，不能省略任何 key
2. Step 5 替换字符串时，先读取原文件再修改，不要整体重写
3. 每个文件修改后立即 npm run build 检查是否有 TS 错误
4. 最终检查：grep 确认无中文硬编码残留在 .tsx 文件中
5. 完成后输出：每个页面的替换 key 数量统计
```
