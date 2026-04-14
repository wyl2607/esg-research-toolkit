# ESG Frontend - Exact Fixes Required

## File: src/i18n/locales/zh.json

### Fix 1: Line 78 (Chinese aiError - change single dash to double dash)

**Location:** `upload.aiError`

**BEFORE:**
```json
78:    "aiError": "AI extraction failed — please check your API configuration",
```

**AFTER:**
```json
78:    "aiError": "AI 提取失败——请检查您的 API 配置",
```

OR if keeping English:
```json
78:    "aiError": "AI extraction failed——please check your API configuration",
```

**Character change:**
- Remove space before `—`: ` — ` → `——`
- OR use double em-dash: `—` → `——`

---

## File: src/i18n/locales/de.json

### Fix 2-7: German Scope Notation (change hyphenated to space-separated)

#### Fix 2: Line 249 (intensity metric)

**BEFORE:**
```json
249:      "intensity": "Emissionsintensität normiert Scope-1-CO₂ auf die Mitarbeiterzahl und ermöglicht einen fairen, größenbereinigten Vergleich zwischen Unternehmen unterschiedlicher Größe."
```

**AFTER:**
```json
249:      "intensity": "Emissionsintensität normiert Scope 1 CO₂ auf die Mitarbeiterzahl und ermöglicht einen fairen, größenbereinigten Vergleich zwischen Unternehmen unterschiedlicher Größe."
```

**Changes:**
- `Scope-1-CO₂` → `Scope 1 CO₂`

---

#### Fix 3: Line 268 (heroImprovingBody)

**BEFORE:**
```json
268:    "heroImprovingBody": "Der Anteil erneuerbarer Energien stieg um {{renewableDelta}}, während Scope-1-Emissionen um {{scope1Delta}} zurückgingen. Das ist aktuell das stärkste positive Signal auf dieser Seite.",
```

**AFTER:**
```json
268:    "heroImprovingBody": "Der Anteil erneuerbarer Energien stieg um {{renewableDelta}}, während Scope 1 Emissionen um {{scope1Delta}} zurückgingen. Das ist aktuell das stärkste positive Signal auf dieser Seite.",
```

**Changes:**
- `Scope-1-Emissionen` → `Scope 1 Emissionen`

---

#### Fix 4: Line 342 (scope1_co2e_tonnes label)

**BEFORE:**
```json
342:      "scope1_co2e_tonnes": "Scope-1-Emissionen",
```

**AFTER:**
```json
342:      "scope1_co2e_tonnes": "Scope 1 Emissionen",
```

**Changes:**
- `Scope-1-Emissionen` → `Scope 1 Emissionen`

---

#### Fix 5: Line 343 (scope2_co2e_tonnes label)

**BEFORE:**
```json
343:      "scope2_co2e_tonnes": "Scope-2-Emissionen",
```

**AFTER:**
```json
343:      "scope2_co2e_tonnes": "Scope 2 Emissionen",
```

**Changes:**
- `Scope-2-Emissionen` → `Scope 2 Emissionen`

---

#### Fix 6: Line 344 (scope3_co2e_tonnes label)

**BEFORE:**
```json
344:      "scope3_co2e_tonnes": "Scope-3-Emissionen",
```

**AFTER:**
```json
344:      "scope3_co2e_tonnes": "Scope 3 Emissionen",
```

**Changes:**
- `Scope-3-Emissionen` → `Scope 3 Emissionen`

---

## Summary of All Fixes

| File | Line | Key | Change | Complexity |
|------|------|-----|--------|------------|
| zh.json | 78 | upload.aiError | Use `——` instead of `—` | Trivial |
| de.json | 249 | metricsExplained.intensity | `Scope-1-CO₂` → `Scope 1 CO₂` | Easy |
| de.json | 268 | profile.heroImprovingBody | `Scope-1-Emissionen` → `Scope 1 Emissionen` | Easy |
| de.json | 342 | company.scope1_co2e_tonnes | `Scope-1-Emissionen` → `Scope 1 Emissionen` | Easy |
| de.json | 343 | company.scope2_co2e_tonnes | `Scope-2-Emissionen` → `Scope 2 Emissionen` | Easy |
| de.json | 344 | company.scope3_co2e_tonnes | `Scope-3-Emissionen` → `Scope 3 Emissionen` | Easy |

**Total changes:** 6 lines across 2 files  
**Estimated time:** 10 minutes  
**Testing time:** 30 minutes  

---

## Optional: Em-Dash Standardization (If choosing global ` — ` format)

If you decide to standardize em-dashes globally to ` — ` (space-dash-space):

### Chinese (zh.json) - Lines 427-432

**BEFORE:**
```json
427:    "networkError": "网络错误——请检查网络连接",
428:    "serverError": "服务器错误（{{status}}）——请稍后重试",
432:    "rateLimited": "请求频率超限——请稍后重试",
```

**AFTER:**
```json
427:    "networkError": "网络错误 — 请检查网络连接",
428:    "serverError": "服务器错误（{{status}}） — 请稍后重试",
432:    "rateLimited": "请求频率超限 — 请稍后重试",
```

**Changes:**
- `——` → ` — ` (double dash → single dash with spaces)

---

## Verification Steps

After making changes:

```bash
# 1. Verify Chinese dash fix
grep -n "aiError" src/i18n/locales/zh.json
# Should show: "aiError": "... ——..." (double dash)

# 2. Verify German Scope notation
grep -n "Scope [0-9]" src/i18n/locales/de.json | grep -v "Scope-"
# Should show: "Scope 1", "Scope 2", "Scope 3" (all space-separated)

# 3. Check no Scope-X patterns remain
grep -n "Scope-[0-9]" src/i18n/locales/de.json
# Should return: 0 results

# 4. Validate JSON syntax
npm run build || npx tsc --noEmit
```

---

## Testing in Browser

After deployment:

1. **Navigate to UploadPage**
   - Trigger an AI extraction error
   - Verify error message displays correctly

2. **Navigate to CompanyProfilePage**
   - Check Scope 1, 2, 3 metrics display
   - Verify em-dashes render properly

3. **Navigate to TaxonomyPage**
   - Check metric descriptions
   - Verify Scope notation in tooltips

4. **Check all tooltips**
   - Hover over metrics
   - Verify em-dashes and Scope notation

5. **Mobile testing**
   - Test on iOS and Android
   - Verify dash rendering on small screens

---

## Rollback Plan

If issues occur:

```bash
# Restore from backup
cp src/i18n/locales/zh.json.backup src/i18n/locales/zh.json
cp src/i18n/locales/de.json.backup src/i18n/locales/de.json

# Or revert specific git commits
git checkout HEAD -- src/i18n/locales/zh.json
git checkout HEAD -- src/i18n/locales/de.json
```

---

## Sign-off

- [ ] Changes reviewed
- [ ] JSON syntax validated
- [ ] Tested in browser (EN)
- [ ] Tested in browser (DE)
- [ ] Tested in browser (ZH)
- [ ] Mobile tested
- [ ] Ready for production

