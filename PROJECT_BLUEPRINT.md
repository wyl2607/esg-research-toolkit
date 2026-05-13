# ESG Research Toolkit Project Blueprint

## Project Mission

ESG Research Toolkit exists to turn public corporate sustainability disclosures
into evidence-backed, multi-period, multi-framework company analysis.

The project should be credible as both a portfolio-grade analysis engine and a
future lightweight regulatory intelligence product. Its strongest wedge is not
generic dashboard polish; it is the ability to explain how a company's
disclosure quality, sustainability signal, and regulatory readiness change over
time with traceable source evidence.

## Product Promise

The first product promise is:

> Show how a company's sustainability disclosure and regulatory readiness
> changed over time, and explain why.

This promise should guide feature selection. Prefer work that strengthens:

- public-disclosure ingestion and analyst review
- reporting-period and company-history consistency
- evidence anchors for important claims and metrics
- framework-aware scoring across EU Taxonomy, CSRC, and CSRD/ESRS surfaces
- company profile, comparison, and export workflows that make analysis usable

## What This Project Should Avoid First

The project should not lead with heavyweight enterprise workflow features before
the analysis engine is dependable. Defer broad investments in:

- login, billing, permissions, and organization management
- generic CRM-style workflow plumbing
- unsupported third-party data aggregation
- UI-only polish that does not improve evidence, period, framework, or analyst
  workflow quality

## Rebuild Requirements

If rebuilt from this blueprint, the first usable implementation must provide:

- a FastAPI backend for report parsing, company records, taxonomy scoring,
  framework comparison, disclosure review, and techno-economic analysis
- a React frontend for upload, pending disclosure review, company history,
  dashboard, comparison, taxonomy, and renewable-economics workflows
- SQLite-backed local persistence plus exportable report artifacts
- explicit official-source guardrails for auto-fetched disclosures
- validation coverage for backend contracts and primary frontend workflows
- compact project records that keep current state separate from long-term
  intent

## Automation Operating Contract

Automation may help advance this project through bounded, validation-backed
task packets. A valid automation packet should:

- target one project and one clear subsystem at a time
- name the files to inspect and the files expected to change
- preserve public/private and source/runtime boundaries
- run the smallest meaningful validation gate before claiming completion
- avoid push, PR, deploy, sync, SSH, rsync, destructive Git, or remote mutation
  unless explicitly approved for that exact action

Multi-project rollout should stay disabled until this project has a clean
project-specific task packet and current local gates are green.

## Current Strategic Order

Use this order when choosing between otherwise valid tasks:

1. Harden history, period, evidence, and framework contracts.
2. Make company profile and comparison views consume those contracts cleanly.
3. Improve analyst confidence through workflow-level frontend tests.
4. Polish loading, empty, and error states on core analyst routes.
5. Improve public README/demo narrative only after the analysis flow is solid.

## Source Of Truth Split

Use this file for durable project purpose and rebuildable intent.

Use current-state files and task records for implementation status, validation
results, incidents, and the next active task. Do not turn this blueprint into a
changelog.
