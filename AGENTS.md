# ESG Research Toolkit — AGENTS Entry

## Load Order

1. `~/AGENTS.md`
2. `tools/automation/workspace-guides/project-records-standard.md`
3. `PROJECT_PROGRESS.md`
4. `INCIDENT_LOG.md` (if present)

## Record Contract (Mandatory)

- `PROJECT_PROGRESS.md` / `INCIDENT_LOG.md` only store code-related, verifiable truth.
- One status item has one canonical location; link elsewhere instead of copy-paste duplication.
- If state is unchanged, do not append new dated prose.

## Reliability Guardrail (Mandatory)

- For any remote deploy/build/ops task, run `scripts/preflight_safe_exec.sh --preflight-only` before actual execution.
- Use explicit `user@ip` or `user@fqdn`; avoid local SSH aliases in automation.
- Use `{{COMPOSE}}` placeholder (resolved by preflight script) instead of hardcoding `docker compose`/`docker-compose`.
- Treat DNS-to-expected-IP mismatch as warning unless task explicitly requires direct-IP DNS.

## Size Guardrails

- `PROJECT_PROGRESS.md`: target <= 120 lines, hard cap <= 200
- `INCIDENT_LOG.md`: target <= 120 lines, hard cap <= 220

## Active Development Exception

- While this project is actively developing, target overflow is allowed temporarily.
- Hard caps still cannot be exceeded.

## Completion Trigger (Auto-required)

When this project is declared phase-complete/release-ready, the same session must:

1. archive detailed history
2. compact records to operator-current view
3. pass strict check:

```bash
bash /Users/yumei/tools/automation/scripts/check-records-compact.sh --strict-target /Users/yumei/projects/esg-research-toolkit
```

If strict check fails, do not mark completion yet.
