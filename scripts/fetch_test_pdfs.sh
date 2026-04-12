#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-data/reports/test_sources}"
mkdir -p "$OUT_DIR"

# filename|url
SOURCES=(
  "catl_2025_sustainability_report.pdf|https://www.catl.com/en/uploads/1/file/public/202603/20260331135628_dciihbv1qr.pdf"
  "catl_2024_sustainability_report.pdf|https://www.catl.com/en/uploads/1/file/public/202505/20250514174222_ndwyqrs061.pdf"
  "catl_2023_sustainability_report.pdf|https://www.catl.com/en/uploads/1/file/public/202404/20240417102933_uuiks9ljr8.pdf"
  "catl_2022_sustainability_report.pdf|https://www.catl.com/en/uploads/1/file/public/202304/20230412124641_cxg8mo2in8.pdf"
  "volkswagen_2024_esrs_sustainability_report.pdf|https://annualreport2024.volkswagen-group.com/_assets/downloads/esrs-sustainability-report-vw-ar24.pdf"
  "byd_2024_sustainability_report.pdf|https://www.byd.com/content/dam/byd-site/jp/sustainable-future/Report2024.pdf"
)

echo "Downloading test PDFs to: $OUT_DIR"
for row in "${SOURCES[@]}"; do
  name="${row%%|*}"
  url="${row##*|}"
  dest="$OUT_DIR/$name"
  echo "- $name"
  curl -L -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)' --retry 2 --connect-timeout 20 --max-time 300 -o "$dest" "$url"
  bytes=$(wc -c <"$dest" | tr -d ' ')
  if [[ "$bytes" -lt 500000 ]]; then
    echo "  ! Warning: small file ($bytes bytes). Source may have anti-bot protection."
  else
    echo "  ✓ $bytes bytes"
  fi

done

echo "Done."
