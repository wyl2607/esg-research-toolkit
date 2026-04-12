#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
PDF_DIR="${PDF_DIR:-data/reports/test_sources}"
TIMEOUT_SEC="${TIMEOUT_SEC:-300}"
POLL_INTERVAL="${POLL_INTERVAL:-2}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== ESG chain debug runner =="
echo "API_BASE=$API_BASE"
echo "PDF_DIR=$PDF_DIR"

if [[ ! -d "$PDF_DIR" ]] || [[ -z "$(find "$PDF_DIR" -maxdepth 1 -name '*.pdf' -print -quit 2>/dev/null)" ]]; then
  echo "[1/4] Downloading test PDFs..."
  bash scripts/fetch_test_pdfs.sh "$PDF_DIR"
else
  echo "[1/4] Using existing local test PDFs"
fi

single_pdf="$PDF_DIR/catl_2024_sustainability_report.pdf"
if [[ ! -f "$single_pdf" ]]; then
  echo "Missing required file: $single_pdf"
  exit 1
fi

echo "[2/4] Single upload smoke test: $(basename "$single_pdf")"
single_http=$(curl -s -o /tmp/esg_single_upload.json -w '%{http_code}' -F "file=@$single_pdf" "$API_BASE/report/upload" || true)
echo "single_http=$single_http"
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('/tmp/esg_single_upload.json')
if not p.exists():
    print('single_response=missing')
    raise SystemExit(0)
text=p.read_text(encoding='utf-8', errors='ignore')
try:
    obj=json.loads(text)
except Exception:
    print('single_response_non_json', text[:240])
    raise SystemExit(0)
if isinstance(obj, dict):
    if 'detail' in obj:
        print('single_error', obj.get('detail'))
    else:
        print('single_ok', obj.get('company_name'), obj.get('report_year'), obj.get('scope1_co2e_tonnes'), obj.get('scope2_co2e_tonnes'))
PY

batch_files=(
  "$PDF_DIR/catl_2025_sustainability_report.pdf"
  "$PDF_DIR/volkswagen_2024_esrs_sustainability_report.pdf"
  "$PDF_DIR/byd_2024_sustainability_report.pdf"
)

curl_args=()
for f in "${batch_files[@]}"; do
  if [[ -f "$f" ]]; then
    curl_args+=( -F "files=@$f" )
  fi
done

if [[ ${#curl_args[@]} -lt 2 ]]; then
  echo "Need at least 2 batch PDFs; found ${#curl_args[@]}"
  exit 1
fi

echo "[3/4] Submit batch upload (${#curl_args[@]} files)"
batch_http=$(curl -s -o /tmp/esg_batch_submit.json -w '%{http_code}' "${curl_args[@]}" "$API_BASE/report/upload/batch" || true)
echo "batch_http=$batch_http"

batch_id=$(python3 - <<'PY'
import json, pathlib
p=pathlib.Path('/tmp/esg_batch_submit.json')
if not p.exists():
    print('')
    raise SystemExit(0)
try:
    obj=json.loads(p.read_text(encoding='utf-8', errors='ignore'))
except Exception:
    print('')
    raise SystemExit(0)
print(obj.get('batch_id',''))
PY
)

if [[ -z "$batch_id" ]]; then
  echo "Batch submit did not return batch_id"
  head -c 400 /tmp/esg_batch_submit.json || true
  echo
  exit 1
fi

echo "batch_id=$batch_id"
echo "[4/4] Polling batch status..."

start_ts=$(date +%s)
while true; do
  status_http=$(curl -s -o /tmp/esg_batch_status.json -w '%{http_code}' "$API_BASE/report/jobs/$batch_id" || true)
  now_ts=$(date +%s)
  elapsed=$((now_ts-start_ts))

  python3 - <<'PY'
import json, pathlib
p=pathlib.Path('/tmp/esg_batch_status.json')
try:
    obj=json.loads(p.read_text(encoding='utf-8', errors='ignore'))
except Exception:
    print('status_non_json')
    raise SystemExit(0)
if 'detail' in obj:
    print('status_error', obj['detail'])
    raise SystemExit(0)
print('progress', obj.get('progress_pct'), 'queued', obj.get('queued_jobs'), 'running', obj.get('running_jobs'), 'completed', obj.get('completed_jobs'), 'failed', obj.get('failed_jobs'))
PY

  done=$(python3 - <<'PY'
import json, pathlib
obj=json.loads(pathlib.Path('/tmp/esg_batch_status.json').read_text(encoding='utf-8', errors='ignore'))
print((obj.get('completed_jobs',0) + obj.get('failed_jobs',0)) >= obj.get('total_jobs',0))
PY
)

  if [[ "$done" == "True" ]]; then
    echo "Batch finished in ${elapsed}s"
    python3 - <<'PY'
import json, pathlib
obj=json.loads(pathlib.Path('/tmp/esg_batch_status.json').read_text(encoding='utf-8', errors='ignore'))
for j in obj.get('jobs',[]):
    print('-', j.get('filename'), j.get('status'), 'duration=', j.get('duration_seconds'), 'error=', j.get('error'))
PY
    break
  fi

  if [[ $elapsed -ge $TIMEOUT_SEC ]]; then
    echo "Batch polling timeout after ${TIMEOUT_SEC}s"
    exit 1
  fi

  sleep "$POLL_INTERVAL"
done

echo "Done."
