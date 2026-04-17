# Dev Tasks — Morning Iteration Queue

Token-efficient workflow: **you run the script → paste the short stdout +
the produced markdown file back to Claude → Claude审核 and gives next step**.

All scripts in this folder are **READ-ONLY侦测脚本**. They never modify
source files, database, or push anything. Output is a markdown report
under `docs/dev-tasks/` or `docs/exec-plans/`.

## Execution Order (明早开工顺序)

| # | Script | Time | What it does | Output |
|---|---|---|---|---|
| 1 | `01_company_identity_audit.py` | ~3 s | Finds SAP/SAP SE, VW Group/AG, etc. split records | `docs/dev-tasks/01_identity_merge_proposals.md` |
| 2 | `02_seed_gap_analysis.py` | ~3 s | Manifest vs DB diff + suggests prior-year URLs | `docs/dev-tasks/02_seed_gap_analysis.md` |
| 3 | `03_ui_autopolish_run.sh` | ~90 s | Screenshots + vision critique | `docs/exec-plans/ui_autopolish_tasks.md` |

## How to Run (one at a time)

```bash
# Task 1
OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/01_company_identity_audit.py
cat docs/dev-tasks/01_identity_merge_proposals.md
# → paste stdout + first 50 lines of the .md back to Claude

# Task 2 (do after Claude reviews Task 1 output)
OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/02_seed_gap_analysis.py
cat docs/dev-tasks/02_seed_gap_analysis.md

# Task 3 (network + API key required)
bash scripts/dev_tasks/03_ui_autopolish_run.sh
cat docs/exec-plans/ui_autopolish_tasks.md | head -100
```

## Why This Design

- **只读侦测**: 脚本产生的只是*提案*，所有实际代码改动由我审核后用 Edit 工具精确下达。
- **独立输出**: 每步的 markdown 都能独立阅读，不需要你记住上一步结果。
- **token 节省**: 你不用把 DB 内容或源码粘给我，只粘脚本输出。
- **可重复**: 修复后再跑同一个脚本，直接看 diff 就知道是否收敛。

## After All Three Complete

Claude 会基于三份报告合并出一个下一阶段的 `docs/exec-plans/` 计划文档，
列出：
- 哪些 identity 合并要动 `company_identity.py`
- 哪些 seed entry 要加到 manifest
- 哪些 UI 任务要进 Phase 3

然后进入 **执行阶段**（我写代码 → Codex review → commit）。
