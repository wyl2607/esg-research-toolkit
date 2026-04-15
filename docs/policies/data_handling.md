# Data Handling Policy

> **Scope**: How raw PDFs, extracted structured data, and audit reports are stored,
> isolated, and shared between local dev / VPS demo / GitHub repo.
>
> **Last updated**: 2026-04-15

---

## TL;DR

- **GitHub repo** = code only. **Never** push PDFs, DB dumps, audit JSON, or extraction artifacts.
- **Local dev** (this machine) = source of truth for raw PDFs, audit reports, working DB.
- **US VPS demo** = receives only **verified, exported** structured data.
  PDFs are **lazy-fetched** from the public IR URL on first request, then cached locally on the VPS.

---

## Three-Tier Storage Model

| Tier | Content | Location | Git? | Sync to VPS? |
|---|---|---|---|---|
| **L1 — Raw PDFs (immutable)** | Original sustainability/annual reports | `data/raw_pdfs/<sha256>.pdf` | ❌ | ❌ (lazy fetch from public URL) |
| **L2 — Structured extractions** | DB rows + JSON snapshots | `data/esg_toolkit.db` + `data/extractions/<sha256>.json` | ❌ | ✅ (after verification) |
| **L3 — Audit / validation reports** | per-company markdown + run history | `scripts/seed_data/audit_reports/` | ❌ (only `.gitkeep`) | ❌ (local debugging only) |
| **Code / manifest** | scripts, schemas, manifest.json | repo | ✅ | ✅ via `git pull` |

---

## Compliance Notes

### Public sustainability PDFs (RWE, BASF, Volkswagen, etc.)

- **GDPR**: not in scope — sustainability reports contain only aggregated corporate data, no PII.
- **Copyright**: published under "all rights reserved" but use for research / personal demo
  is defensible under fair use / quotation right (§51 UrhG in Germany).
- **Mirroring**: avoid creating a public mirror of any single company's PDF on the VPS.
  Always **lazy-fetch from the public IR URL** so the VPS acts as a cache + proxy, not a redistribution point.
- **Robots.txt**: respect it. The seed downloader in `scripts/seed_german_demo.py` already uses a browser User-Agent;
  if a publisher explicitly disallows, drop them from the manifest.

### What MUST NOT enter git

```
data/raw_pdfs/**          (PDFs)
data/extractions/**       (JSON snapshots — may contain large extracted text)
data/exports/**           (DB dumps for VPS sync)
*.db / *.sqlite           (working DB)
PROJECT_PROGRESS.md       (local notes; may contain VPS IPs)
INCIDENT_LOG.md           (local; may contain failure traces)
scripts/seed_data/pdfs/**/*.pdf
scripts/seed_data/audit_reports/*.md
```

All of the above are already in `.gitignore`. Pre-push guard:
`scripts/security_check.sh && scripts/review_push_guard.sh origin/main`.

---

## VPS Sync Workflow (manual, gated)

```
[local]                                          [VPS]
─────                                            ─────
1. seed_german_demo.py --validate
2. audit_extractions.py
3. run_audit_iterations.py --iterations 3 --apply
4. validate_benchmarks.py        →  status=ok
5. export_verified.py            →  data/exports/YYYY-MM-DD.sql.gz + manifest.json
6. sync_to_vps.sh <host>         →  scp + ssh import     ──►  import_verified.py
                                                              recompute_benchmarks
                                                              first profile request
                                                              triggers PDF lazy-fetch
                                                              from public URL
```

**Rules**:
- Sync is **always manual** (never automated). Each push represents an explicit "ready to publish" decision.
- The export script **only includes rows that passed the latest audit run** (high-confidence verdicts).
- The VPS never receives PDFs from local — VPS fetches from the public IR URL on demand.
- If a public URL is dead, that company is **not visible on the demo**. Better to show fewer companies than stale ones.

---

## When This Policy Changes

- Adding a new tier (e.g., vector embeddings, LLM-generated summaries) → update this file first, then `.gitignore`.
- Migrating storage backend (SQLite → Postgres, local FS → S3) → update the table above and the runbook.
- Any change that affects what crosses the local / VPS / GitHub boundary requires updating BOTH this file
  AND `scripts/security_check.sh` if it introduces new file patterns to guard against.
