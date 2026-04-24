#!/usr/bin/env bash
# consistency_check.sh — ESG-Research-Toolkit SSoT 守卫脚本 (CR-05)
#
# 依据 docs/policies/project-consistency-rules.md §1 实施下列 grep-based 规则:
#   a. esg_frameworks/*.py 中 framework_version 字面量（禁止硬编码，除 schemas.py）
#   b. FRAMEWORK_VERSIONS 映射字面量拷贝（除 schemas.py）
#   c. frontend/src/pages/*.tsx 未引入 useTranslation 但含非 ASCII UI 字面量
#   d. report_parser/ 下有 APIRouter 定义但未被 main.py include 的孤立 router
#   e. frontend/src/i18n/locales/{en,de,zh}.json 顶层 key 集合必须严格相等
#
# Usage:
#   bash scripts/consistency_check.sh
# 可在 scripts/review_push_guard.sh 里 source 接入 pre-push gate.
#
# Exit codes:
#   0            无违规
#   1..255       违规条数 (超过 255 仍输出上限 255)
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

violations=0
report() {
  printf '[consistency] RULE=%s FILE=%s LINE=%s DETAIL=%s\n' "$1" "$2" "$3" "$4"
  violations=$((violations + 1))
}

# --- Rule (a): framework_version hardcoded literal in scorer files ----------
while IFS=: read -r file line match; do
  [[ -z "$file" ]] && continue
  [[ "$file" == *schemas.py ]] && continue
  report a "$file" "$line" "$match"
done < <(grep -rnE 'framework_version\s*=\s*["'"'"'][^"'"'"']+["'"'"']' esg_frameworks/ 2>/dev/null || true)

# --- Rule (b): duplicate FRAMEWORK_VERSIONS map literals --------------------
# Look for "<framework_id>": "<version>" patterns known from schemas.py, anywhere in repo except schemas.py
patterns=(
  '"eu_taxonomy"\s*:\s*"2020/852"'
  '"csrd"\s*:\s*"ESRS-2024"'
  '"csrc_2023"\s*:\s*"2023"'
  '"gri_universal"\s*:\s*"GRI-2021"'
  '"sec_climate"\s*:\s*"SEC-2024"'
  '"sasb_standards"\s*:\s*"SASB-2023"'
)
for pat in "${patterns[@]}"; do
  while IFS=: read -r file line match; do
    [[ -z "$file" ]] && continue
    [[ "$file" == *schemas.py ]] && continue
    [[ "$file" == *.pyc ]] && continue
    [[ "$file" == *__pycache__* ]] && continue
    # Tests legitimately mirror canonical values to assert the contract
    [[ "$file" == ./tests/* || "$file" == tests/* ]] && continue
    report b "$file" "$line" "$match"
  done < <(grep -rnE "$pat" --include='*.py' . 2>/dev/null || true)
done

# --- Rule (c): i18n gaps in pages -------------------------------------------
for page in frontend/src/pages/*.tsx; do
  [[ -f "$page" ]] || continue
  if ! grep -q 'useTranslation' "$page"; then
    # non-ASCII printable-ish chars
    if LC_ALL=C grep -nP '[^\x00-\x7F]' "$page" >/dev/null 2>&1; then
      first_line=$(LC_ALL=C grep -nP '[^\x00-\x7F]' "$page" | head -1 | cut -d: -f1)
      report c "$page" "${first_line:-1}" "missing useTranslation + contains non-ASCII literals"
    fi
  fi
done

# --- Rule (d): orphan routers in report_parser ------------------------------
for routerfile in $(grep -lE 'APIRouter\s*\(' report_parser/*.py 2>/dev/null || true); do
  if git check-ignore -q -- "$routerfile"; then
    continue
  fi
  mod_basename="$(basename "$routerfile" .py)"
  # skip the canonical api.py (it's the main mounted one)
  [[ "$mod_basename" == "api" ]] && continue
  # Check if ANY python file (main.py or other router files) imports this module
  if ! grep -rqE "from report_parser\.$mod_basename\s+import|import report_parser\.$mod_basename" \
       --include='*.py' main.py report_parser/ 2>/dev/null; then
    report d "$routerfile" 1 "router defined but not imported by main.py or any report_parser module"
  fi
done

# --- Rule (e): i18n locale key parity ---------------------------------------
LOCALE_DIR="frontend/src/i18n/locales"
if [[ -f "$LOCALE_DIR/en.json" && -f "$LOCALE_DIR/de.json" && -f "$LOCALE_DIR/zh.json" ]]; then
  parity_out="$(python3 - <<'PYEOF' 2>&1 || true
import json, sys, pathlib
root = pathlib.Path("frontend/src/i18n/locales")
locales = {k: json.loads((root / f"{k}.json").read_text()) for k in ("en", "de", "zh")}
keys = {k: set(v.keys()) for k, v in locales.items()}
all_keys = keys["en"] | keys["de"] | keys["zh"]
mismatches = []
for k in all_keys:
    missing = [lang for lang in ("en", "de", "zh") if k not in keys[lang]]
    if missing:
        mismatches.append(f"{k} missing in {','.join(missing)}")
for m in mismatches:
    print(m)
PYEOF
)"
  if [[ -n "$parity_out" ]]; then
    while IFS= read -r detail; do
      [[ -z "$detail" ]] && continue
      report e "$LOCALE_DIR" 1 "$detail"
    done <<< "$parity_out"
  fi
fi

# --- Summary ----------------------------------------------------------------
printf '[consistency] total_violations=%d\n' "$violations"
[[ $violations -gt 255 ]] && exit 255
exit "$violations"
