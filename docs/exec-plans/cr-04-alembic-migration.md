# CR-04 — Alembic Formal Migration Cutover

**Status**: Plan v1 (2026-04-20)
**Owner**: Claude local（高风险 DB 迁移，按 §7 不外包）
**Scope source**: `docs/policies/project-consistency-rules.md` §5 + §7 CR-04

---

## Goal

把 `core/database.py` 里的 runtime additive schema helpers 替换为标准 Alembic 迁移流程。

## Current state (survey output)

- 仓库**无** `alembic/` 目录或 `alembic.ini`
- `init_db()` (`core/database.py:41`) 调 `Base.metadata.create_all` + 两个 runtime 助手：
  - `ensure_storage_schema` (`report_parser/storage.py:578`)
  - `ensure_framework_storage_schema` (`esg_frameworks/storage.py:166`)
- `ENFORCE_MIGRATION_GATE` flag 已存在（`core/config.py:19`，默认 `False`）
- `scripts/migrate_db.py` — 裸 `ALTER TABLE` wrapper，已基本被 runtime 助手取代
- `main.py:179` 启动时调 `init_db()`
- `tests/conftest.py` 极简；测试依赖 `init_db()` 在 per-test sqlite 上即时建表

## Implementation Plan (8 steps, risk-ranked)

1. **[low] Bootstrap Alembic**
   - 新建 `alembic.ini` + `alembic/{env.py,script.py.mako,versions/}`
   - `env.py` target = `core.database.Base.metadata`；URL = `settings.database_url`
   - `render_as_batch=True`（sqlite ALTER 兼容）
   - Verify: `alembic current` on fresh sqlite 不报错
   - Rollback: 删 `alembic/` 和 `alembic.ini`

2. **[high] 生成 baseline revision `0001_baseline`**
   - 在 empty DB 上先跑 `Base.metadata.create_all` + 两个 `ensure_*`，再 `alembic revision --autogenerate`
   - 手工 review 产物，把 data-backfill ops（`payload_hash` / `source_doc_key` 回填）挪到 `upgrade()` 里 `op.execute(...)`，并加 "table has rows" 守卫
   - Verify: `pytest -x` 全绿；`alembic upgrade head` 产生的 schema 与旧 `init_db()` `sqlite3 .schema` diff 为空
   - Rollback: 删 revision 文件
   - **Reversible flag**: 在 `core/config.py` 引入 `USE_ALEMBIC_INIT` (默认 `false`)

3. **[high] 创建 `0002_retire_runtime_helpers`**（文档 no-op revision）
   - Refactor `init_db()`: `USE_ALEMBIC_INIT=true` → 调 `command.upgrade(cfg, "head")`；否则沿用旧路径
   - `ensure_storage_schema` / `ensure_framework_storage_schema` 改为：检测 `alembic_version` 表存在则 no-op
   - Verify: `pytest` 全绿；prod-snapshot clone 手测
   - Rollback: flag 置 false

4. **[medium] Fresh-dev-clone bootstrap**
   - `scripts/db_init.sh` 跑 `alembic upgrade head`
   - `scripts/migrate_db.py` 改为 shim，print "use `alembic upgrade head`" + exit 0（保留避免破坏既有 runbook）
   - README + `docs/runbooks/postgres_migration.md` 同步
   - Verify: 删 `data/esg_toolkit.db` → `bash scripts/db_init.sh` → `pytest` 全绿

5. **[high] In-memory sqlite 测试路径**
   - `tests/conftest.py` 加 `migrated_engine` fixture：`command.upgrade(cfg, "head")` 跑在 in-memory / tmp-file sqlite
   - Session-scoped 模板 DB + copy-on-use 加速
   - Verify: full `pytest` 绿；`tests/test_report_parser.py::...`（line 1508 引用 `ensure_storage_schema` 的用例）
   - Rollback: fixture 可禁用

6. **[high] 生产环境 cutover path**
   - `docs/runbooks/alembic_cutover.md` 新增
   - 已存在 prod DB：`alembic stamp 0001_baseline` 跳过 baseline，后续增量跑 head
   - Verify: prod-snapshot 拷贝上 stamp + upgrade，前后 `sqlite3 .schema` diff 为空
   - Rollback: `alembic downgrade base` + 删 `alembic_version` 表

7. **[medium] Flip the gate**
   - 经过一个 release cycle staging 开启后，`ENFORCE_MIGRATION_GATE` 默认改 `True`
   - 移除 `USE_ALEMBIC_INIT` toggle
   - 清空两个 `ensure_*` helper 正文，留 stub 抛 `DeprecationWarning`
   - Rollback: 还原 config 默认；flag 保留一个 release

8. **[medium] 测试覆盖增量**
   - `tests/test_migrations.py`：
     - `test_fresh_db_upgrade_head` — 空 sqlite → upgrade → schema 等于 `Base.metadata`
     - `test_existing_db_stamp_then_upgrade` — `tests/fixtures/legacy_esg.db` 快照 → stamp → upgrade → no drift + 数据保留
     - `test_idempotent_rerun` — `upgrade head` 跑两次幂等
     - `test_downgrade_base` — 完整反向

## Reversible feature flags

- `USE_ALEMBIC_INIT`（步骤 3-6）：启动时用 Alembic 还是老路径
- `ENFORCE_MIGRATION_GATE`（现有）：硬闸；步骤 7 前保持默认 off

## Critical files

- `core/database.py` / `core/config.py`
- `report_parser/storage.py` / `esg_frameworks/storage.py`
- `tests/conftest.py`
- `alembic/`（新建）

## Entry gate

当前仓库 168 tests passing、consistency_check 0 violations、frontend build clean。CR-04 启动前应 snapshot 一份 prod DB 到 `tests/fixtures/legacy_esg.db` 作为步骤 6 / 步骤 8 测试材料。
