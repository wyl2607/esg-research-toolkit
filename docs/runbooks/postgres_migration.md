# Postgres Migration Runbook (VPS-only)

> **当前默认**：本地 + VPS 都跑 SQLite (`data/esg_toolkit.db`)。
> **迁移目标**：当 VPS 公司数 > 50 或并发读 > 20 时，**只在 VPS** 切到 Postgres，
> 本地继续 SQLite 不变。
>
> **阻塞条件**：必须先把所有 schema 改动通过 `report_parser.storage.ensure_storage_schema`
> 用 `Base.metadata.create_all` 重建一遍——已经做了，所以 ExtractionRun 表会自动创建。

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
# 1. 装 Postgres 16
apt-get update && apt-get install -y postgresql-16 postgresql-contrib

# 2. 建库 + 用户
sudo -u postgres psql <<SQL
CREATE USER esg WITH PASSWORD '<change-me>';
CREATE DATABASE esg_toolkit OWNER esg;
GRANT ALL PRIVILEGES ON DATABASE esg_toolkit TO esg;
SQL

# 3. 装 psycopg
/opt/esg-toolkit/.venv/bin/pip install 'psycopg[binary]>=3.1'
```

---

## 3. 切换 DATABASE_URL

代码已经 Postgres-ready（`core/database.py` 自动开 `pool_size=10, max_overflow=20, pool_recycle=1800`）。

VPS `.env`：

```
DATABASE_URL=postgresql+psycopg://esg:<change-me>@127.0.0.1:5432/esg_toolkit
```

第一次启动会自动 `create_all` 所有表（`company_reports`, `extraction_runs`, `industry_benchmarks`）。

---

## 4. 数据迁移（可选）

如果 VPS 已经有 SQLite 数据要保留：

```bash
# 在 VPS 的旧 SQLite 模式下
.venv/bin/python scripts/export_verified.py --out /tmp/migrate

# 切 DATABASE_URL 到 Postgres，重启 uvicorn

# 导入
.venv/bin/python scripts/import_verified.py /tmp/migrate/<timestamp>/
curl -X POST http://127.0.0.1:8000/benchmarks/recompute
```

如果 VPS 是新装的，跳过此步——下一次本地 `sync_to_vps.sh` 会自动灌数据。

---

## 5. 验证

```bash
psql -U esg -d esg_toolkit -c '\dt'
# 期望：company_reports, extraction_runs, industry_benchmarks, ...

curl http://127.0.0.1:8000/benchmarks/D35.11
# 期望：返回 metric 列表
```

---

## 6. 回退

```bash
# 改回 .env
DATABASE_URL=sqlite:///./data/esg_toolkit.db

# 重启 uvicorn
# Postgres 数据保留，下次启动重新生效
```

---

## 7. 不要做的事

- ❌ 不要在本地切 Postgres——本地 SQLite 单文件够用，迁移没收益
- ❌ 不要把 Postgres 端口 5432 开到公网，永远走 127.0.0.1
- ❌ 不要把 DATABASE_URL 写进 git——只在 VPS 本地 `.env` 里
- ❌ 不要在 Postgres 上跑 `ensure_storage_schema` 的 SQLite-only `ALTER TABLE`——已经被 dialect.name guard 保护
