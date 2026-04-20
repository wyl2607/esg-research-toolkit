# Postgres Migration Runbook (VPS-only, Alembic-first)

> **当前默认**：本地 + VPS 都跑 SQLite (`data/esg_toolkit.db`)。  
> **迁移目标**：当 VPS 公司数 > 50 或并发读 > 20 时，**只在 VPS** 切到 Postgres，  
> 本地继续 SQLite 不变。

---

## 1. 触发条件（不要提前迁移）

| 指标 | 阈值 | 当前 |
|---|---|---|
| `company_reports` 行数 | > 50 | 20 |
| 并发读 RPS | > 20 | 未知（单 worker） |
| `/benchmarks/recompute` 耗时 | > 5s | < 1s |
| 数据库锁等待 | 出现 | 无 |

**任意两项达标再启动迁移**，否则 SQLite 维护成本更低。

---

## 2. 准备 VPS

```bash
# 1) 装 Postgres 16
apt-get update && apt-get install -y postgresql-16 postgresql-contrib

# 2) 建库 + 用户
sudo -u postgres psql <<SQL
CREATE USER esg WITH PASSWORD '<change-me>';
CREATE DATABASE esg_toolkit OWNER esg;
GRANT ALL PRIVILEGES ON DATABASE esg_toolkit TO esg;
SQL

# 3) 装 psycopg
/opt/esg-toolkit/.venv/bin/pip install 'psycopg[binary]>=3.1'
```

---

## 3. 切换 DATABASE_URL

VPS `.env`：

```bash
DATABASE_URL=postgresql+psycopg://esg:<change-me>@127.0.0.1:5432/esg_toolkit
```

---

## 4. 初始化/升级 schema（Alembic）

```bash
# 推荐：项目脚本（幂等）
./scripts/db_init.sh

# 等价命令
alembic upgrade head
```

如果是**已有生产库**（库里已存在历史表/数据），不要直接 upgrade，按：

- `docs/runbooks/alembic_cutover.md`

执行 `alembic stamp 0001_baseline` 后再 `alembic upgrade head`。

兼容提示：

- `scripts/migrate_db.py` 仅保留为 legacy shim，会打印 Alembic 指引并 `exit 0`，**不会写 schema**。

---

## 5. 数据迁移（可选）

如果 VPS 旧 SQLite 数据要保留：

```bash
# 在旧 SQLite 模式导出
.venv/bin/python scripts/export_verified.py --out /tmp/migrate

# 切 DATABASE_URL 到 Postgres，执行第 4 步 Alembic 初始化后重启服务

# 导入并重算
.venv/bin/python scripts/import_verified.py /tmp/migrate/<timestamp>/
curl -X POST http://127.0.0.1:8000/benchmarks/recompute
```

---

## 6. 验证

```bash
alembic current
# 期望: head revision (当前为 0002_retire_runtime_helpers)

psql -U esg -d esg_toolkit -c '\dt'
# 期望: company_reports, extraction_runs, framework_analysis_results, pending_disclosures, ...

curl http://127.0.0.1:8000/benchmarks/D35.11
# 期望: 返回 metric 列表
```

---

## 7. 回退

```bash
# 改回 SQLite
DATABASE_URL=sqlite:///./data/esg_toolkit.db
```

重启服务后即可回退到 SQLite。  
若 Postgres 侧 schema/数据异常，按变更前备份恢复（见 `alembic_cutover.md` 回退说明）。

---

## 8. 不要做的事

- ❌ 不要在本地切 Postgres（本地 SQLite 单文件维护更轻）
- ❌ 不要把 Postgres 5432 端口暴露公网（仅 127.0.0.1）
- ❌ 不要把 `DATABASE_URL` 提交到 git
- ❌ 不要把 `scripts/migrate_db.py` 当作真实迁移入口（它是 shim）
