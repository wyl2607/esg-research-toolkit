# Alembic Cutover Runbook (existing production DB)

适用场景：生产库已存在历史表和数据，需要切到 Alembic 管理且避免重复建表。

---

## 1. 前置检查与备份

```bash
# 在目标环境中
alembic current || true
pg_dump -Fc -f /tmp/esg_toolkit_pre_alembic_cutover.dump esg_toolkit
```

确认：

- `DATABASE_URL` 已指向目标生产 Postgres。
- 已完成业务低峰窗口与回退窗口安排。

---

## 2. 对齐基线（不改 schema）

```bash
alembic stamp 0001_baseline
```

说明：

- `stamp` 只写 `alembic_version`，不执行 DDL。
- 用于告诉 Alembic：当前库视为已处于 baseline。

---

## 3. 升级到最新版本

```bash
alembic upgrade head
```

当前链路下，这一步会把版本推进到 head（当前为 `0002_retire_runtime_helpers`）。

---

## 4. 验证

```bash
alembic current
alembic heads

psql -d esg_toolkit -c 'SELECT version_num FROM alembic_version;'
psql -d esg_toolkit -c '\dt'
```

验收要点：

- `alembic current` 与 `alembic heads` 一致（在 head）。
- `alembic_version.version_num` 为 head revision。
- 关键业务表仍可读写，应用健康检查通过。

---

## 5. 回退说明

优先策略：**恢复备份**（推荐，最稳妥）。

```bash
# 示例：先 drop/recreate 目标库后导回
pg_restore --clean --if-exists -d esg_toolkit /tmp/esg_toolkit_pre_alembic_cutover.dump
```

补充说明：

- `alembic downgrade` 只回退 migration 脚本定义的内容，不保证恢复所有业务数据变更。
- 本项目 legacy 脚本 `scripts/migrate_db.py` 是兼容 shim（仅提示，不写 schema）。
