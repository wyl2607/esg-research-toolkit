# UI Design System Review — ESG Research Toolkit

**Reviewer**: Claude (视觉 + 设计一致性审查)
**Method**: `preview_screenshot` 穿 10 个主要页面 (Dashboard / Companies / Compare / Benchmark / Frameworks / Taxonomy / Upload / CompanyProfile / ManualCaseBuilder / LCOE)
**Scope**: 系统性视觉/信息架构不一致，而非单条 CRITICAL。
**Status**: Plan-only（本文档不包含代码改动，改动分三期执行）

---

## 1. 核心诊断（一句话）

> **项目没有统一的容器、卡片、标题、Banner 系统。** 每个页面各自决定 `max-w-*`、padding、标题尺寸、信息条样式，导致整体感觉像 10 个人写的 10 个产品。

这和 v0.2.2 / Round 2 已经做的"局部 polish"不在同一层级 —— 局部调完后短期好看，但只要新增一页就会再次发散。必须先立系统、再继续 polish。

---

## 2. 系统性不一致矩阵

下表列出 5 个"本该全局统一但没有"的维度，和每页当前实现：

| 维度 | Dashboard | Companies | Compare | Benchmark | Frameworks | Taxonomy | Upload | CompanyProfile | Manual | LCOE |
|---|---|---|---|---|---|---|---|---|---|---|
| 页面容器宽度 | full | full | full | full | 半-窄 + 右侧大空白 | `max-w-5xl mx-auto` | full | full | full | full |
| 标题尺寸 | text-3xl | text-5xl md+ | text-5xl md+ | text-3xl | text-5xl md+ | text-3xl | text-3xl | serif display (公司名) | text-3xl | text-3xl |
| KPI 卡 | 大号 text-5xl | p-4 text-3xl | — | — | — | MetricCard 组件 | — | CompanyProfile header KPI (text-lg) | — | — |
| 控制栏 (filter/selector) | — | surface-card 内含 flex-wrap 2 排 | surface-card p-5 | 裸 inline flex | rounded-2xl p-6 | surface-card max-w-3xl | div 横排 | — | Card 2 列 | Card 2 列 |
| 信息/提示条 | — | — | — | amber alert 中部 | — | stone 中性 | yellow tip 右侧 | emerald "Kernaussage" | amber 顶部 strip | amber 顶部 strip |

**结论**：
- **容器宽度**：1 种（Taxonomy）用 `max-w-5xl`，其他 9 种各不相同。
- **标题**：至少 4 种尺寸（text-3xl / text-5xl / serif display / 公司名字体）。
- **Banner**：5 种完全不同的视觉语言表达同一件事（info / warning / meta）。
- **Filter bar**：7 种实现，没有共用组件。

---

## 3. 全局 Design Tokens（建议新增）

### 3.1 容器层 (`PageContainer`)

```tsx
// frontend/src/components/layout/PageContainer.tsx
type Width = 'default' | 'wide' | 'narrow'
// default: max-w-6xl (主要分析页，1152px)
// wide:    max-w-7xl (密集表格 / benchmark)
// narrow:  max-w-3xl (仅表单/引导页：Upload / Taxonomy 选择态)
<PageContainer width="default"> ... </PageContainer>
```

所有页面组件的 **第一层 div 换成 `<PageContainer>`**，`Layout` 内部已有左 sidebar，不需要再多容器。

### 3.2 页面头部 (`PageHeader`)

```tsx
<PageHeader
  kicker="OFFENLEGUNGSANALYSE"
  title="Unternehmen"
  subtitle="……"
  actions={<Button>CSV exportieren</Button>}
  kpis={[{label, value}, …]}  // optional，最多 4 张
/>
```

**硬性规则**：
- 标题永远 `text-3xl md:text-4xl font-semibold text-slate-900`（不要 text-5xl — 5xl 在 1200px 宽下太抢眼）。
- subtitle 永远 `text-sm leading-6 text-slate-600 max-w-2xl`。
- KPI 数字永远 `numeric-mono text-3xl font-semibold`。
- 头部永远 `mb-8`，和下面内容隔开一个固定距离。
- 当 `kpis` 存在时，在 `lg:` 以上横排右对齐，在 `md` 以下移到 title 下方换行（避免像 Companies 页那样 title 被挤窄）。

### 3.3 卡片/容器 (`SurfaceCard` 变体)

当前 `.surface-card` 被滥用。拆 3 变体：

| 变体 | 用法 | padding |
|---|---|---|
| `<Panel>` | 内容区主容器（表格、图表、长内容） | `p-6` |
| `<FormCard>` | 选择器 / 过滤器 / 短表单 | `p-5` |
| `<StatCard>` | KPI 单格 | `p-4` |

每个变体 border/shadow/radius 固定：`rounded-2xl border border-slate-200 shadow-sm bg-white`。

### 3.4 Banner / 信息条 (`NoticeBanner`)

**统一 5 种信息条成 1 个组件 × 4 个语义**：

```tsx
<NoticeBanner tone="info" | "warning" | "success" | "mode">
  {children}
</NoticeBanner>
```

| tone | 用途 | 色 |
|---|---|---|
| `info` | 中性说明（Taxonomy 目前的 stone） | slate-200/slate-50 |
| `warning` | 小样本 / 需谨慎解读（Benchmark） | amber-300/amber-50 |
| `success` | 核心正面洞察（CompanyProfile "Kernaussage"） | emerald-300/emerald-50 |
| `mode` | 页面模式提示（LCOE/Manual "Projektanalyse-Modus"） | violet-300/violet-50 |

全部 `rounded-2xl px-5 py-3 text-sm leading-6`，差异只在边框/背景色。

### 3.5 Filter Bar (`FilterBar`)

所有选择器/过滤器/按钮组用同一个容器：

```tsx
<FilterBar>
  <FilterBar.Field label="Branche"><Select>…</Select></FilterBar.Field>
  <FilterBar.Field label="Jahr"><Select>…</Select></FilterBar.Field>
  <FilterBar.Actions>
    <Button variant="primary">Neu berechnen</Button>
  </FilterBar.Actions>
</FilterBar>
```

在 `md:` 以上横排，`sm:` 以下自动竖排，`FilterBar.Actions` 靠右。

---

## 4. 逐页诊断 + 修复清单

### 4.1 Dashboard
- **诊断**：KPI 数字非常大但卡片 padding 松散，看起来像不同尺寸。
- **修复**：套 `<PageHeader>`（带 KPI prop）+ 把 3 张 KPI 换成 `<StatCard>`。

### 4.2 Companies
- **诊断**：
  - 公司卡里的 metric 小卡文字被硬截断（"SCOPE 1" / "MITARB EITEND" 被拆成 2 行）—— 这是 `section-kicker` 的 `tracking-[0.2em]` + 狭窄列宽冲突。
  - 3 列网格在 1200px 下把每个 metric 格挤到 ~80px，必然换行。
- **修复**：
  - CompanyCard 内部 metric 改 2 列 `sm:grid-cols-2`，不上 3 列。
  - 或者 metric 改横排小 pill（label: value 一行），抛弃卡中卡。
  - Header 套 `<PageHeader kpis={...}>`，title 自动归位 text-3xl。

### 4.3 Compare
- **诊断**：
  - 标题 text-5xl 在 1200px 下显得过大，"Unternehmensvergleich" 占掉 50% 高度。
  - 选择器卡是 full 宽，但 chip 20+ 个在 1200 以上换 3 行，在 1400+ 又浪费。
  - CTA `Vergleich starten` 在 disabled 时几乎看不见（bg-slate-200 on cream background）。
- **修复**：
  - Header 用 `<PageHeader>` 回归 text-3xl md:text-4xl。
  - Chip 网格改 `grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2`，公司一致等宽。
  - Disabled CTA 改 `bg-slate-100 text-slate-400 border border-slate-200` 以拉开与背景对比。

### 4.4 Benchmark
- **诊断**：
  - Filter 是裸 inline flex，没有卡片壳 —— 和其他页的 selector 感觉不同层级。
  - 警示条 (amber) 不走 `NoticeBanner` 统一。
- **修复**：Filter 套 `<FilterBar>`，警示换 `<NoticeBanner tone="warning">`。

### 4.5 Frameworks
- **诊断**：
  - 选择器 `max-w-3xl` + 右侧大块空白，视觉上像 "半个页面挂了"。
  - Empty state 卡 `max-w-2xl` 又窄了一级，和选择器宽度不一致。
- **修复**：
  - 页面套 `<PageContainer width="default">`（max-w-6xl），选择器 `<FormCard>` 取消 max-w-3xl，让它撑满。
  - Empty state 也用 `<FormCard>` 保持同宽。

### 4.6 Taxonomy
- **诊断**：上一轮已做 `max-w-5xl`，但：
  - 选择器 `max-w-3xl` < 容器宽度，"锯齿边"只部分解决（disclaimer 和 KPI grid 仍 full 宽）。
- **修复**：统一全部块到 `max-w-5xl` 或者改 PageContainer default；选择器去掉 max-w 自适应。

### 4.7 Upload
- **诊断**：
  - 黄色 tip 在右侧飘浮，和 NACE select 宽度不协调，手机端会被挤到下面但字号不变。
  - 上传拖拽区 dashed border + 图标 + 文本，padding 不对齐 filter card。
- **修复**：
  - Tip 改 `<NoticeBanner tone="info">` 放 form 上方全宽。
  - 拖拽区统一 `<Panel>` 样式，dashed border 作为内层。

### 4.8 CompanyProfile
- **诊断**：
  - 头部巨大 surface-card 里塞"公司名 serif + 年份徽章 + 2 KPI + 2 导出按钮"，层级混乱。
  - "Kernaussage" emerald panel 没有统一的 Banner 语言。
  - 下方"Identität & Herkunft" 子面板又换一套 card 样式。
- **修复**：
  - Header 拆成 `<PageHeader>`（title + 年份 badge + KPI + actions）。
  - Kernaussage 换 `<NoticeBanner tone="success">`。
  - 下方所有分块统一成 `<Panel>` + `<PanelHeader>`（title + icon）。

### 4.9 ManualCaseBuilder
- **诊断**：
  - 顶部 "Projektanalyse-Modus" 黄条 + "Workflow ohne Modellkontingent" badge + kicker + 标题 —— 4 层 meta 信息堆在一起。
  - 右侧 "Letzte Unternehmen" pill 列表 宽度 = 33%，和左侧 form 没有明显视觉层级。
- **修复**：
  - 顶部 mode 条换 `<NoticeBanner tone="mode">`，badge 取消（冗余）。
  - 右侧改成固定 280px 侧栏 `<Panel>`，避免宽度跟随百分比摇摆。

### 4.10 LCOE
- **诊断**：
  - 同 Manual 的 mode 条问题。
  - 右侧"Berechnete Ergebnisse" 在 empty 态下是一个大 dashed 框 "Keine Daten verfügbar"，和 Compare/Frameworks 的 empty 卡不一样。
- **修复**：mode 条用 `<NoticeBanner tone="mode">`；右侧 empty 用 QueryStateCard（已有）保持一致。

---

## 5. 分期执行计划（不要一次性大重构）

### Phase 1 — 立 Token（~半天，纯新增，不改现有页面）

1. 新增 `frontend/src/components/layout/PageContainer.tsx`
2. 新增 `frontend/src/components/layout/PageHeader.tsx`
3. 新增 `frontend/src/components/layout/Panel.tsx` / `FormCard.tsx` / `StatCard.tsx`
4. 新增 `frontend/src/components/NoticeBanner.tsx`
5. 新增 `frontend/src/components/FilterBar.tsx`
6. 写对应 Storybook / MDX 示例（或 `docs/design-docs/components.md`）

**验证**：这些都是新组件，现有页面不受影响；跑 `npm run lint && npm run build` 通过即可。

### Phase 2 — 逐页迁移（每页 1 个独立 commit）

优先级（按用户可见度排序）：

1. Dashboard
2. Companies ← 最严重
3. CompanyProfile ← 最复杂
4. Compare
5. Frameworks
6. Taxonomy
7. Benchmark
8. Upload
9. Manual / LCOE（项目模式，展示优先级较低）

每页 commit：
- Before/After 截图放到 commit message（或 `docs/design-docs/screenshots/<page>-{before,after}.png`）
- 跑 `npm run lint && build && test:smoke`

### Phase 3 — 清理（~半天）

1. 删掉未被引用的 `.surface-card` / `.editorial-panel` CSS utility（或 deprecate 为别名）
2. 在 `eslint` 配置里加自定义规则：禁止在页面组件顶层直接用 `max-w-*`（必须走 PageContainer）
3. 更新 `docs/design-docs/ui_design_system.md`（本文档）中的 Phase 状态

---

## 6. 成功标准

- [ ] 10 个主要页面顶层全部套 `<PageContainer>` + `<PageHeader>`
- [ ] `rg "surface-card" frontend/src/pages` 为空（完成 Panel 替换后）
- [ ] `rg "max-w-(xl|2xl|3xl|4xl|5xl|6xl|7xl)" frontend/src/pages` 只出现在 `<PageContainer width="...">` 内
- [ ] 5 个信息条色系全部收敛到 `<NoticeBanner>` 4 种 tone
- [ ] `npm run test:smoke` 20+ passed；新增 Playwright a11y check：每页 h1 只有 1 个且 text-3xl md:text-4xl
- [ ] 手机 (375px)、平板 (768px)、桌面 (1280px) 三档截图并排无明显宽度不一

---

## 7. 需要用户决策的开放问题

1. **serif display 字体**（CompanyProfile 上的公司名）留还是弃？是编辑风格特色还是历史遗留？建议：只保留在 CompanyProfile header，其他全部走 sans。
2. **kicker 文字**（"OFFENLEGUNGSANALYSE" 等 0.2em tracking 小标签）是否每页都要？如果要保留，应进 PageHeader prop。
3. **sidebar 宽度**（当前 ~240px 偏窄，右侧内容区被拉长）是否调整为 260px 以容纳更长的德语菜单项？
4. **是否引入 Storybook**？如果要做组件库，Storybook 能把 token 约束住；如果只是单项目，MDX 示例足够。

---

## 8. 下一步（等用户决策后）

用户回答 §7 后：
- 我起草 Phase 1 PR（纯新增，低风险）。
- Phase 2 按页推进，每次 1 commit，你审 screenshot。
- 全程不碰现有 tests（只在 Phase 3 末补 a11y 断言）。
