# ESG Research Toolkit — AGENTS Entry

## Load Order

1. `~/AGENTS.md`
2. `.local/engineering-records/CANONICAL_MEMORY.md`（本地工程记录，canonical source）
3. `.guard/ENGINEERING_MEMORY.md`（本地记忆，若存在）
4. `tools/automation/workspace-guides/project-records-standard.md`（参考）

## Record Contract (Mandatory)

- 本项目工程过程记录默认写入 `.local/engineering-records/`（不上传）。
- 仅在明确需要公开同步时，才新增/更新仓库内公开记录文档。
- One status item has one canonical location; link elsewhere instead of copy-paste duplication.
- If state is unchanged, do not append new dated prose.

## Reliability Guardrail (Mandatory)

- For any remote deploy/build/ops task, run `scripts/preflight_safe_exec.sh --preflight-only` before actual execution.
- Use explicit `user@ip` or `user@fqdn`; avoid local SSH aliases in automation.
- Use `{{COMPOSE}}` placeholder (resolved by preflight script) instead of hardcoding `docker compose`/`docker-compose`.
- Treat DNS-to-expected-IP mismatch as warning unless task explicitly requires direct-IP DNS.

## Push Review Gate (Mandatory)

- Before push, run `scripts/review_push_guard.sh origin/main`.
- Never push local-only files or conversational/non-engineering prose.
- Every changed file must be classified (`public` or `local`) via `.guard/*-prefixes.txt` rules; unclassified files must not be pushed.

## Size Guardrails

- 本地工程记录按主题拆分，避免单文件过大（建议单文件 <= 200 行）

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
