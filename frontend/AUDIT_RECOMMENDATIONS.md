# Design Consistency Audit - Implementation Recommendations

## Quick Reference: Issues Found

### 🔴 MUST FIX (Priority 1)

#### Issue 1A: Em-dash with spaces (EN/DE) vs without spaces (ZH)
**Lines affected:**
- EN: 76, 158, 160, 185, 240-244, 425-429
- DE: 78, 242-245, 427-432
- ZH: 427-432

**Current inconsistency:**
```
EN: "Network error — please check your connection"          (space-dash-space)
DE: "Netzwerkfehler — bitte Verbindung prüfen"              (space-dash-space)
ZH: "网络错误——请检查网络连接"                              (no-space-double-dash-no-space)
```

**RECOMMENDED FIX:**
Choose ONE approach globally:

**Option A: Standardize to ` — ` (space-dash-space) everywhere**
```json
// en.json (no changes needed)
"networkError": "Network error — please check your connection"

// de.json (no changes needed)
"networkError": "Netzwerkfehler — bitte Verbindung prüfen"

// zh.json - CHANGE FROM:
"networkError": "网络错误——请检查网络连接"
// TO:
"networkError": "网络错误 — 请检查网络连接"
```

**Option B: Maintain language conventions (RECOMMENDED FOR UX)**
- EN/DE: Keep ` — ` (professional typographic standard)
- ZH: Keep `——` (Chinese typography convention) or `—` (consistent with EN/DE)

**Affected entries in zh.json to fix if choosing Option B:**
- Line 78: `aiError` (currently has single `—`, should have `——` to match error style)

---

#### Issue 1B: Chinese aiError inconsistency
**Current state (line 78 in zh.json):**
```json
"aiError": "AI extraction failed — please check your API configuration"
```
**Should be:**
```json
"aiError": "AI 提取失败——请检查您的 API 配置"
```
OR maintain the current English format if using dual-language content.

---

### 🟡 SHOULD FIX (Priority 2)

#### Issue 2: German Scope notation inconsistency
**Problem:** German uses both `Scope 1` and `Scope-1` inconsistently

**Current code in de.json:**
```json
// Line 215 - Consistent (space-separated)
"scope1": "Scope 1 (tCO₂e)"

// Line 249 - INCONSISTENT (hyphenated)
"intensity": "Emissionsintensität normiert Scope-1-CO₂ auf die Mitarbeiterzahl..."

// Line 268 - INCONSISTENT (hyphenated)
"heroImprovingBody": "Der Anteil erneuerbarer Energien stieg um {{renewableDelta}}, während Scope-1-Emissionen um {{scope1Delta}} zurückgingen..."

// Lines 342-344 - INCONSISTENT (hyphenated)
"scope1_co2e_tonnes": "Scope-1-Emissionen"
"scope2_co2e_tonnes": "Scope-2-Emissionen"
"scope3_co2e_tonnes": "Scope-3-Emissionen"
```

**RECOMMENDED FIX: Standardize to space-separated format**

Change de.json:
```json
// Line 249 - CHANGE FROM:
"intensity": "Emissionsintensität normiert Scope-1-CO₂ auf die Mitarbeiterzahl..."
// TO:
"intensity": "Emissionsintensität normiert Scope 1 CO₂ auf die Mitarbeiterzahl..."

// Line 268 - CHANGE FROM:
"heroImprovingBody": "Der Anteil erneuerbarer Energien stieg um {{renewableDelta}}, während Scope-1-Emissionen um {{scope1Delta}} zurückgingen..."
// TO:
"heroImprovingBody": "Der Anteil erneuerbarer Energien stieg um {{renewableDelta}}, während Scope 1 Emissionen um {{scope1Delta}} zurückgingen..."

// Lines 342-344 - CHANGE FROM:
"scope1_co2e_tonnes": "Scope-1-Emissionen"
"scope2_co2e_tonnes": "Scope-2-Emissionen"
"scope3_co2e_tonnes": "Scope-3-Emissionen"
// TO:
"scope1_co2e_tonnes": "Scope 1 Emissionen"
"scope2_co2e_tonnes": "Scope 2 Emissionen"
"scope3_co2e_tonnes": "Scope 3 Emissionen"
```

---

### ✅ NO CHANGES NEEDED (Priority 3)

#### Issue 4: Arrow usage ✓
- Already consistent across all languages (3 usages)
- Serves clear semantic purpose

#### Issue 5: Checkmarks/X-marks ✓
- Already perfectly consistent
- Used in identical contexts across all languages

#### Issue 6: Currency/Units ✓
- Formatting is consistent (€/kW, €/MWh, etc.)
- All locales maintain the same format

#### Issue 7: Emojis ✓
- Technology options have identical emojis across all languages
- All 4 technologies have matching emojis

#### Issue 8: Page structure ✓
- All pages follow consistent kicker + title + subtitle pattern
- CSS classes are standardized

---

## Implementation Steps

### Step 1: Back up current locale files
```bash
cp src/i18n/locales/en.json src/i18n/locales/en.json.backup
cp src/i18n/locales/de.json src/i18n/locales/de.json.backup
cp src/i18n/locales/zh.json src/i18n/locales/zh.json.backup
```

### Step 2: Fix Priority 1 Issues

**For Chinese (zh.json):**
- Line 78: Update aiError to use consistent punctuation
- Lines 427-432: Verify error messages use consistent dash style

**For English & German:** 
- No changes needed if keeping space-dash-space format (` — `)

### Step 3: Fix Priority 2 Issues

**For German (de.json):**
- Line 249: `Scope-1-CO₂` → `Scope 1 CO₂`
- Line 268: `Scope-1-Emissionen` → `Scope 1 Emissionen`
- Lines 342-344: Update all `Scope-X-Emissionen` to `Scope X Emissionen`

### Step 4: Verify in UI

Test the following pages/components:
1. **TaxonomyPage** - Check Scope notation rendering
2. **UploadPage** - Test error messages display
3. **LcoePage** - Verify em-dashes in descriptions
4. **CompanyProfilePage** - Check Scope metrics display

### Step 5: Browser Testing
- Chrome, Safari, Firefox on desktop
- Mobile browsers (iOS Safari, Chrome Mobile)
- Check em-dash rendering in tooltips, cards, and modals

---

## Verification Commands

After making changes, run these to verify consistency:

```bash
# Check all em-dashes
echo "=== EM-DASHES IN en.json ===" && grep -c " — " src/i18n/locales/en.json
echo "=== EM-DASHES IN de.json ===" && grep -c " — " src/i18n/locales/de.json
echo "=== DASHES IN zh.json ===" && grep -c "——" src/i18n/locales/zh.json

# Check Scope notation
echo "=== SCOPE VARIANTS ===" && \
  echo "Scope 1 (space-separated):" && grep -c "Scope 1" src/i18n/locales/de.json && \
  echo "Scope-1 (hyphenated):" && grep -c "Scope-1" src/i18n/locales/de.json

# Check for any remaining inconsistencies in error messages
echo "=== ERROR MESSAGE PUNCTUATION ===" && \
  grep -n "networkError\|serverError\|rateLimited" src/i18n/locales/zh.json
```

---

## Design Rationale

### Why these fixes matter:

1. **Professional appearance:** Consistent punctuation enhances perceived quality
2. **Accessibility:** Screen readers render dashes differently based on spacing
3. **Internationalization:** Shows respect for language-specific typography conventions
4. **Maintainability:** Consistent patterns are easier to maintain going forward
5. **Brand consistency:** Unified style across user-facing text

---

## Example: After Fix

### English (en.json) - No changes
```json
"networkError": "Network error — please check your connection",
"aiError": "AI extraction failed — please check your API configuration",
"scope1": "Scope 1 — Direct greenhouse gas emissions..."
```

### German (de.json) - Scope notation fixed
```json
"networkError": "Netzwerkfehler — bitte Verbindung prüfen",
"aiError": "KI-Extraktion fehlgeschlagen — bitte API-Konfiguration prüfen",
"scope1": "Scope 1 — Direkte Treibhausgasemissionen...",
"intensity": "Emissionsintensität normiert Scope 1 CO₂ auf die Mitarbeiterzahl...",
"heroImprovingBody": "...während Scope 1 Emissionen um {{scope1Delta}} zurückgingen...",
"scope1_co2e_tonnes": "Scope 1 Emissionen"
```

### Chinese (zh.json) - Error punctuation fixed
```json
"networkError": "网络错误——请检查网络连接",
"aiError": "AI 提取失败——请检查您的 API 配置",
"serverError": "服务器错误（{{status}}）——请稍后重试",
"rateLimited": "请求频率超限——请稍后重试"
```

---

## Related Files for Future Reference

- **Main audit report:** `DESIGN_CONSISTENCY_AUDIT.md`
- **Page components:** `src/pages/*.tsx` (all follow consistent structure)
- **UI components:** `src/components/ui/*` (standardized styling)
- **Translation files:** `src/i18n/locales/{en,de,zh}.json`

---

**Status:** Ready for implementation  
**Est. Time to Fix:** 15-20 minutes  
**Testing Time:** 30 minutes  
**Total Effort:** ~1 hour
