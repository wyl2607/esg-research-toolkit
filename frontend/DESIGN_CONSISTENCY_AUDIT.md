# ESG Frontend: Design Consistency Audit Report

**Date:** 2024  
**Scope:** Page components (src/pages/) and i18n locales (en.json, zh.json, de.json)  
**Status:** COMPREHENSIVE AUDIT COMPLETED

---

## Executive Summary

This audit identified **7 major design consistency issues** across the ESG frontend, primarily in:
- **Multi-language punctuation inconsistency** (em-dashes, spaces)
- **Scope notation variants** (Scope 1 vs Scope-1)
- **Missing em-dashes in Chinese error messages**
- **Inconsistent arrow usage patterns**
- **Currency and unit formatting** (generally consistent)
- **Emoji implementation** (highly consistent across languages)
- **Page component structure** (highly consistent)

---

## Issue Catalog

### **ISSUE 1: Inconsistent Em-Dash Punctuation Across Languages**

**Severity:** MEDIUM  
**Category:** Punctuation & Formatting

#### Current State:
- **English (en.json):** Uses ` — ` (single em-dash with spaces on both sides)
- **German (de.json):** Uses ` — ` (single em-dash with spaces on both sides)  
- **Chinese (zh.json):** Uses `——` (double em-dashes with NO spaces) OR `—` (single em-dash with no spaces)

#### Affected Files & Lines:

**English (src/i18n/locales/en.json):**
- Line 76: `"aiError": "AI extraction failed — please check your API configuration"`
- Line 158: `"deMarketRefNote": "Source: EPEX SPOT ... Not from company reports — set manually."`
- Line 160: `"cnMarketRefNote": "Source: CEPCI / NEA ... Prices in CNY/MWh. Not from company reports — set manually."`
- Line 185: `"electricity_price_eur_per_mwh": "... Not extracted from company reports — must be set manually or via..."`
- Lines 240-244: Scope 1-3 descriptions, revenueAligned, renewable metrics
- Line 425: `"networkError": "Network error — please check your connection"`
- Line 426: `"serverError": "Server error ({{status}}) — please try again"`
- Line 429: `"rateLimited": "Rate limit exceeded — please retry in a moment"`

**German (src/i18n/locales/de.json):**
- Line 78: `"aiError": "KI-Extraktion fehlgeschlagen — bitte API-Konfiguration prüfen"`
- Lines 242-245: Scope descriptions (using ` — `)
- Line 427: `"networkError": "Netzwerkfehler — bitte Verbindung prüfen"`
- Line 428: `"serverError": "Serverfehler ({{status}}) — bitte erneut versuchen"`
- Line 432: `"rateLimited": "Anfragelimit überschritten — bitte kurz warten"`

**Chinese (src/i18n/locales/zh.json):**
- Line 78: `"aiError": "AI extraction failed — ..."` (has SINGLE em-dash `—`, inconsistent with error messages)
- Line 427: `"networkError": "网络错误——请检查网络连接"` (has DOUBLE em-dash `——`, no spaces)
- Line 428: `"serverError": "服务器错误（{{status}}）——请稍后重试"` (has DOUBLE em-dash `——`, no spaces)
- Line 432: `"rateLimited": "请求频率超限——请稍后重试"` (has DOUBLE em-dash `——`, no spaces)

#### Recommended Fix:
1. **Standardize globally:** Choose ONE em-dash format: ` — ` (em-dash with spaces) for all languages
2. **OR maintain language-specific conventions:**
   - English/German: ` — ` (em-dash with spaces)
   - Chinese: `——` (double em-dash, no spaces) or `—` (single em-dash, no spaces)
3. **Priority:** Fix `upload.aiError` in Chinese (line 78) to match error message style

**Verification Commands:**
```bash
grep -n "—" src/i18n/locales/en.json | wc -l     # Count: 12
grep -n "—" src/i18n/locales/de.json | wc -l     # Count: 9
grep -n "——" src/i18n/locales/zh.json | wc -l    # Count: em-dashes
```

---

### **ISSUE 2: Inconsistent Scope Notation (Scope 1 vs Scope-1)**

**Severity:** MEDIUM  
**Category:** Naming & Typography

#### Current State:
- **English (en.json):** Consistently uses `Scope 1`, `Scope 2`, `Scope 3` (space-separated)
- **German (de.json):** **MIXED** - uses both `Scope 1` AND `Scope-1` in different contexts
- **Chinese (zh.json):** Consistently uses `范围一`, `范围二`, `范围三` (Chinese characters, no English variants)

#### Affected Files & Lines:

**German (de.json):**
- Line 215: `"scope1": "Scope 1 (tCO₂e)"` → Space-separated
- Line 249: `"intensity": "Emissionsintensität normiert Scope-1-CO₂ auf..."` → **Hyphenated**
- Line 268: `"heroImprovingBody": "... während Scope-1-Emissionen..."` → **Hyphenated**
- Line 342: `"scope1_co2e_tonnes": "Scope-1-Emissionen"` → **Hyphenated**
- Line 343: `"scope2_co2e_tonnes": "Scope-2-Emissionen"` → **Hyphenated**
- Line 344: `"scope3_co2e_tonnes": "Scope-3-Emissionen"` → **Hyphenated**

**Pattern Analysis:**
- When "Scope" appears standalone in labels → Space-separated `Scope 1`
- When "Scope" is used in compound descriptions (e.g., "Scope-1-Emissionen") → Hyphenated `Scope-1`
- This is NOT consistent with English or any established convention

#### Recommended Fix:
**Option A (Recommended):** Standardize on space-separated format across all contexts
- Line 249: Change `Scope-1-CO₂` to `Scope 1 CO₂`
- Line 268: Change `Scope-1-Emissionen` to `Scope 1 Emissionen`
- Lines 342-344: Change `Scope-1-Emissionen` to `Scope 1 Emissionen`, etc.

**Option B:** Maintain hyphenated format only in compound words (adjective form)
- Keep labels as `Scope 1`
- Use hyphenated only when it modifies a noun (e.g., "Scope-1-Emissionen")
- Apply consistently across ALL languages

**Verification Commands:**
```bash
grep -n "Scope-" src/i18n/locales/de.json      # Shows all hyphenated variants
grep -n "Scope [0-9]" src/i18n/locales/de.json # Shows all space-separated variants
```

---

### **ISSUE 3: Missing Em-Dashes in Chinese Error Messages (Language-Specific)**

**Severity:** MEDIUM  
**Category:** Punctuation Consistency, Localization

#### Current State:
The `upload.aiError` key uses a SINGLE em-dash `—` while ALL other error messages use double em-dashes `——`.

#### Affected Files & Lines:

**Chinese (src/i18n/locales/zh.json):**
- Line 78: `"aiError": "AI extraction failed — please check your API configuration"`
  - Contains: Single em-dash `—` (U+2014) with NO spaces
  - **Expected:** Should match error message style (double em-dash `——` or consistent single em-dash)

**Related consistent error messages:**
- Line 427: `"networkError": "网络错误——请检查网络连接"` ✓ Double em-dash
- Line 428: `"serverError": "服务器错误（{{status}}）——请稍后重试"` ✓ Double em-dash
- Line 432: `"rateLimited": "请求频率超限——请稍后重试"` ✓ Double em-dash
- Line 431: `"backendOffline": "API 服务器不可用——请启动后端"` ✓ Double em-dash

#### Recommended Fix:
**Standardize Chinese error punctuation:**
1. Option A (Recommended): Change line 78 from `—` to `——` to match all other error messages
   ```json
   "aiError": "AI 提取失败——请检查您的 API 配置"
   ```

2. Option B: Change all `——` to ` — ` (single em-dash with spaces) to match English/German convention
   ```json
   "networkError": "网络错误 — 请检查网络连接"
   ```

**Priority:** HIGH - impacts user experience consistency

---

### **ISSUE 4: Arrow (→) Usage Pattern**

**Severity:** LOW  
**Category:** Punctuation & Styling

#### Current State:
Arrows are used consistently but only in **3 specific contexts** across all languages.

#### Affected Files & Lines:

**English (src/i18n/locales/en.json):**
- Line 58: `"runTaxonomy": "Run Taxonomy Score →"`
- Line 82: `"viewTaxonomy": "View Taxonomy →"`
- Line 163: `"fxToEur": "FX rate to EUR (1 unit → EUR)"`

**German (src/i18n/locales/de.json):**
- Line 58: `"runTaxonomy": "Taxonomie-Bewertung starten →"`
- Line 84: `"viewTaxonomy": "Taxonomie-Auswertung →"`
- Line 164: `"fxToEur": "Kurs zu EUR (1 Einheit → EUR)"`

**Chinese (src/i18n/locales/zh.json):**
- Line 58: `"runTaxonomy": "进行分类法评分 →"`
- Line 84: `"viewTaxonomy": "查看分类法评分 →"`
- Line 164: `"fxToEur": "兑欧元汇率（1单位 → EUR）"`

#### Analysis:
✓ **Highly consistent** - All three languages use arrows identically in the same contexts:
- Action buttons pointing to taxonomy analysis
- Exchange rate notation (currency conversion indicator)

#### Recommendation:
**No changes needed** - Pattern is consistent and serves clear semantic purpose (action indication and unit conversion).

---

### **ISSUE 5: Checkmarks (✓) and X-Marks (✗) Usage**

**Severity:** LOW  
**Category:** Symbols & Indicators

#### Current State:
Checkmarks and X-marks are used consistently for DNSH (Do No Significant Harm) status indicators.

#### Affected Files & Lines:

**English (src/i18n/locales/en.json):**
- Line 97: `"dnshPass": "✓ Pass"`
- Line 98: `"dnshFail": "✗ Fail"`

**German (src/i18n/locales/de.json):**
- Line 99: `"dnshPass": "✓ Bestanden"`
- Line 100: `"dnshFail": "✗ Nicht bestanden"`

**Chinese (src/i18n/locales/zh.json):**
- Line 99: `"dnshPass": "✓ 通过"`
- Line 100: `"dnshFail": "✗ 未通过"`

#### Page Implementation:
- **TaxonomyPage.tsx** (line 16): Uses Lucide icons `<CheckCircle>`, `<XCircle>` for visual rendering
- i18n strings are used for text labels only

#### Analysis:
✓ **Perfectly consistent** - Same symbols used across all languages in identical contexts

#### Recommendation:
**No changes needed** - Implementation is optimal and accessible (Unicode symbols + text labels).

---

### **ISSUE 6: Currency and Unit Formatting**

**Severity:** LOW  
**Category:** Data Representation & Formatting

#### Current State:
Currency symbols and units are used consistently across all languages and contexts.

#### Affected Files & Lines (General Pattern - all consistent):

**Currency Formats:**
- `€/kW` - Euro per kilowatt
- `€/kW/yr` - Euro per kilowatt per year
- `€/MWh` - Euro per megawatt-hour
- `CNY/MWh` - Chinese Yuan per megawatt-hour

**Technical Units:**
- `MW` - Megawatts
- `MWh` - Megawatt-hours
- `m³` - Cubic meters (water volume)
- `tCO₂e` - Tonnes of CO2 equivalent
- `CO₂` - Carbon dioxide

**Examples across locales:**

| Key | EN | DE | ZH |
|-----|----|----|-----|
| capex | CapEx (€/kW) | Investitionskosten (€/kW) | 资本支出（€/kW） |
| opex | OpEx (€/kW/yr) | Betriebskosten (€/kW/Jahr) | 运营成本（€/kW/年） |
| scope1 | Scope 1 (tCO₂e) | Scope 1 (tCO₂e) | 范围一排放（tCO₂e） |

#### Analysis:
✓ **Highly consistent** - All three locales maintain identical unit formatting

#### Recommendation:
**No changes needed** - Currency and unit formatting is consistent and professional.

---

### **ISSUE 7: Emoji Implementation in Technology Options**

**Severity:** LOW  
**Category:** Visual Consistency & Accessibility

#### Current State:
Emojis are used in the LCOE calculator's technology selection dropdown.

#### Affected Files & Lines:

**English (src/i18n/locales/en.json, lines 127-130):**
```json
"technologyOptions": {
  "solarPv": "☀️ Solar PV",
  "windOnshore": "🌬️ Wind Onshore",
  "windOffshore": "🌊 Wind Offshore",
  "batteryStorage": "🔋 Battery Storage"
}
```

**German (src/i18n/locales/de.json, lines 129-132):**
```json
"technologyOptions": {
  "solarPv": "☀️ Solar-Photovoltaik",
  "windOnshore": "🌬️ Wind Onshore",
  "windOffshore": "🌊 Wind Offshore",
  "batteryStorage": "🔋 Batteriespeicher"
}
```

**Chinese (src/i18n/locales/zh.json, lines 129-132):**
```json
"technologyOptions": {
  "solarPv": "☀️ 光伏",
  "windOnshore": "🌬️ 陆上风电",
  "windOffshore": "🌊 海上风电",
  "batteryStorage": "🔋 电池储能"
}
```

#### Analysis:
✓ **Perfect consistency** - All languages include identical emojis in the same order and context

#### Page Implementation:
- **LcoePage.tsx** (lines ~127-130): Displays these options in a selector dropdown

#### Recommendation:
**No changes needed** - Emoji implementation is consistent and enhances UX clarity.

---

### **ISSUE 8: Section Headers & Page Structure**

**Severity:** LOW  
**Category:** Component Structure & Layout

#### Current State:
All pages follow consistent structure with `section-kicker` + `title` + `subtitle` pattern.

#### Verified Page Components:

**File: src/pages/*.tsx**
| Page | Kicker | Title | Subtitle | Structure |
|------|--------|-------|----------|-----------|
| CompaniesPage.tsx | ✓ (line 76) | ✓ (line 79) | ✓ (line 81) | Consistent |
| DashboardPage.tsx | ✓ (line 95) | ✓ (line 98) | ✓ (line 99) | Consistent |
| UploadPage.tsx | ✓ (line 122) | ✓ (line 125) | ✓ (line 127) | Consistent |
| TaxonomyPage.tsx | ✓ (line 44) | ✓ (line 47) | ✓ (line 49) | Consistent |
| FrameworksPage.tsx | ✓ (line 188) | ✓ (line 189) | ✓ (line 191) | Consistent |
| ComparePage.tsx | ✓ (line 222) | ✓ (line 223) | ✓ (line 225) | Consistent |
| LcoePage.tsx | ✓ (line 152) | ✓ (line 155) | ✓ (line 156) | Consistent |
| ManualCaseBuilderPage.tsx | ✓ (line 197) | ✓ (line 201) | ✓ (line 205) | Consistent |
| RegionalPage.tsx | ✓ (line 72) | ✓ (line 73) | ✓ (line 75) | Consistent |

#### HTML/CSS Implementation:
All pages use:
- `.section-kicker` for category labels
- `.text-3xl font-semibold` for titles
- `.text-sm leading-6` for subtitles

#### Analysis:
✓ **Excellent consistency** - All pages follow identical structure and styling

#### Recommendation:
**No changes needed** - Page structure is well-standardized.

---

## Summary Table: Issues by Severity

| Issue # | Category | Severity | Impact | Status |
|---------|----------|----------|--------|--------|
| 1 | Punctuation (Em-dash) | **MEDIUM** | 12 EN + 9 DE + 5 ZH entries | NEEDS FIX |
| 2 | Typography (Scope notation) | **MEDIUM** | 6 German entries | NEEDS FIX |
| 3 | Punctuation (Chinese only) | **MEDIUM** | 1 entry (aiError) | NEEDS FIX |
| 4 | Symbols (Arrow) | LOW | 3 entries (consistent) | ✓ OK |
| 5 | Symbols (Checkmarks) | LOW | 2 entries (consistent) | ✓ OK |
| 6 | Units & Currency | LOW | 15 entries (consistent) | ✓ OK |
| 7 | Emojis | LOW | 4 entries (consistent) | ✓ OK |
| 8 | Page Structure | LOW | 9 pages (consistent) | ✓ OK |

---

## Recommended Action Plan

### Priority 1 (HIGH - Fix First)
1. **Standardize em-dash usage globally**
   - Choose: ` — ` (em-dash with spaces) for all languages, OR
   - Maintain language-specific: ` — ` for EN/DE, `——` for ZH
   - Update all error messages and descriptions consistently

2. **Fix Chinese aiError inconsistency**
   - Line 78 in zh.json: Change to match error message punctuation style

### Priority 2 (MEDIUM - Fix After Priority 1)
3. **Standardize German Scope notation**
   - Choose: Either `Scope 1` everywhere OR `Scope-1` in compounds
   - Update lines 249, 268, 342-344 in de.json consistently

### Priority 3 (LOW - Verify)
4. **Verify implementation across UI components**
   - Ensure em-dashes render correctly in all browsers
   - Test Scope notation rendering in charts and tables
   - Verify emoji rendering on different devices

---

## Testing Recommendations

### Before Deployment:
```bash
# Verify em-dash consistency
grep -E "—|——" src/i18n/locales/*.json | sort | uniq -c

# Verify Scope notation
grep -E "Scope[- ][0-9]" src/i18n/locales/*.json

# Check for any remaining inconsistencies
grep -n "error\|Error" src/i18n/locales/zh.json | grep -E "—|——"
```

### Runtime Testing:
- Render all error messages in UI
- Check that em-dashes display correctly in tooltips and descriptions
- Verify Scope notation in charts and metric displays
- Test across browsers (Chrome, Safari, Firefox) and devices

---

## Appendix: Character Reference

**Em-Dash Variants:**
- Single em-dash: `—` (U+2014) "EM DASH"
- Double em-dash: `——` (two U+2014 characters)
- En-dash: `–` (U+2013) "EN DASH"
- Hyphen: `-` (U+002D) "HYPHEN-MINUS"

**Special Symbols:**
- Checkmark: `✓` (U+2713)
- X-mark: `✗` (U+2717)
- Right arrow: `→` (U+2192)

**Currency & Units:**
- Euro: `€` (U+20AC)
- Subscript 2: `₂` (U+2082)
- Superscript e: `ᵉ` (U+1D47) in CO₂e

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024 | Design Audit | Initial comprehensive audit |

---

**End of Report**
