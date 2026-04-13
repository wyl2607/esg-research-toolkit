# Task 27: Analysis Engine Foundation Sprint

**Goal**: align the project with the career-first, moat-first roadmap by implementing the highest-value analysis foundation before auth, billing, or heavy platform features.

**Priority**: P0  
**Estimated effort**: 2-3 focused days or 5-7 implementation sessions  
**Depends on**: current multi-framework and company storage baseline  
**Roadmap anchor**: [CAREER_PRODUCT_ROADMAP.md](../CAREER_PRODUCT_ROADMAP.md)

---

## Why This Task Exists

The project already has:

- company report storage
- multi-framework scoring
- comparison and profile plans

What it does **not** yet fully have is the strongest differentiator:

**history + evidence + version-aware analysis**

This sprint creates that foundation first.

---

## Scope

This task should deliver the minimum architecture needed for:

1. company history across periods
2. evidence traceability for extracted metrics
3. framework-version-aware derived analysis
4. a stronger company profile page later

Do **not** add:

- login
- payment
- team permissions
- admin console
- broad CRM features

---

## Deliverables

### Deliverable 1 — Reporting Period Model

Upgrade persistence so analysis is not tied only to `company_name + report_year`.

Target additions:

- reporting period identity
- report type
- period label
- source document metadata

Suggested shape:

```text
Company
  -> ReportingPeriod
       -> SourceDocument
       -> ExtractedMetric
       -> DerivedAnalysisResult
```

### Deliverable 2 — Evidence Traceability

Each extracted metric should be able to reference:

- source file / source URL
- page number or page range when available
- snippet or extraction note
- extraction time
- confidence or evidence completeness note

### Deliverable 3 — Version-Aware Analysis Results

Derived results should retain:

- framework id
- framework version
- run timestamp
- explanation text
- source reporting period

This makes old results readable after framework updates.

### Deliverable 4 — History API Support

Add or extend APIs so a company page can load:

- all available reporting periods
- key metric trends across time
- derived score trends across time
- evidence-backed drill-down links

---

## Implementation Order

### Step 1 — Review Current Data Surfaces

Inspect and document current structures in:

- `core/schemas.py`
- `report_parser/storage.py`
- `report_parser/api.py`
- `esg_frameworks/`
- `taxonomy_scorer/`

Output:

- list what can be reused
- list what needs new schema fields or tables

### Step 2 — Introduce New Data Structures

Add the minimum new schema/storage support for:

- reporting period
- source document
- evidence metadata
- derived analysis result with framework version

Prefer additive changes over risky rewrites.

### Step 3 — Persist Evidence Metadata

Update ingestion/storage flow so uploaded or fetched reports preserve:

- source identity
- file hash
- document type
- evidence details for extracted metrics where available

### Step 4 — Persist Derived Results

Store analysis outputs so the system can reuse them later rather than recomputing everything on each page load.

### Step 5 — Add Company History Endpoint

Provide one strong backend endpoint for a profile page or demo page, returning:

- company identity
- available periods
- metric history
- score history
- evidence summary
- latest analysis metadata

### Step 6 — Validate Backward Compatibility

Ensure existing list/export/basic company APIs still behave correctly or degrade safely.

---

## Suggested API Direction

You do not need all of these at once, but the end state should support:

- `GET /report/companies/{company_name}/profile`
- `GET /report/companies/{company_name}/history`
- `GET /report/periods/{period_id}/evidence`
- `GET /frameworks/results/{result_id}`

---

## Validation

Run the relevant checks after implementation:

```bash
OPENAI_API_KEY=dummy .venv/bin/pytest -q
cd frontend && npm run build
```

If schema changes are made, also validate:

- historical data still loads
- a new company report can still be stored
- profile/history responses include evidence and period metadata

---

## Done Criteria

- [ ] storage supports reporting-period-aware records
- [ ] evidence metadata exists for extracted metrics or source documents
- [ ] derived results retain framework version information
- [ ] one history/profile API returns multi-period trend-ready data
- [ ] existing tests pass or are updated
- [ ] frontend build still passes if affected

---

## What This Unlocks Next

After this task, the next highest-value tasks are:

1. company profile page as the portfolio centerpiece
2. polished public case studies
3. framework difference explanations
4. peer benchmark starter

That order follows the project’s current strategic roadmap.
