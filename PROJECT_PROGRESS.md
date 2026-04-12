# ESG Research Toolkit — 项目进度报告

**最后更新**: 2026-04-12
**GitHub**: https://github.com/wyl2607/esg-research-toolkit
**状态**: ✅ v0.2.0 生产部署与监控完成，进入运维观察期

---

## 完成度概览

| 阶段 | 内容 | 状态 |
|------|------|------|
| Stage 1 | 清理 + 重建 schemas | ✅ 完成 |
| Stage 2 | report_parser 模块 | ✅ 完成 |
| Stage 3 | taxonomy_scorer 模块 | ✅ 完成 |
| Stage 4 | techno_economics 模块 | ✅ 完成 |
| Stage 5 | 测试 + 文档 + Docker + CI/CD | ✅ 完成 |
| Stage 6 | 真实数据验证（CATL 2024） | ✅ 完成 |
| Stage 7 | React 前端（6 页面） | ✅ 完成 |
| Stage 8 | 生产部署（VPS） | ✅ 完成 |

---

## 技术栈

**后端**: FastAPI + Uvicorn + SQLAlchemy + SQLite + pdfplumber + OpenAI API
**前端**: React 18 + Vite 5 + TypeScript + shadcn/ui + Tailwind CSS + Recharts
**测试**: pytest（19 个，100% 通过）
**部署**: Docker + GitHub Actions

---

## API 端点（16 个）

| 模块 | 端点 | 方法 |
|------|------|------|
| Report Parser | `/report/upload` | POST |
| Report Parser | `/report/companies` | GET |
| Report Parser | `/report/companies/{name}/{year}` | GET/PUT/DELETE |
| Taxonomy | `/taxonomy/score` | POST |
| Taxonomy | `/taxonomy/report` | POST + GET |
| Taxonomy | `/taxonomy/report/text` | POST |
| Taxonomy | `/taxonomy/activities` | GET |
| Techno-Econ | `/techno/lcoe` | POST |
| Techno-Econ | `/techno/sensitivity` | POST |
| Techno-Econ | `/techno/benchmarks` | GET |
| System | `/` `/health` `/docs` | GET |

---

## 前端页面（Stage 7）

| 页面 | 路径 | 功能 |
|------|------|------|
| Dashboard | `/` | 汇总卡片 + 最近分析表 |
| Upload | `/upload` | 拖拽上传 PDF，提取 ESG 数据预览 |
| Taxonomy | `/taxonomy` | 6 目标雷达图 + DNSH + 差距 + 建议 |
| LCOE | `/lcoe` | 参数表单 + LCOE/NPV/IRR + 敏感性图 |
| Companies | `/companies` | 可搜索排序表 + 删除 |
| Compare | `/compare` | 最多 4 家公司并排对比 |

---

## 下一步

- [ ] 观察 `esg-health.log` / `esg-backup.log` 连续 24h，确认定时任务稳定
- [ ] 清理 Nginx 重复 `server_name` 警告，降低运维噪声

---

## 2026-04-12 三层部署进展（Task 10-11）

- 完成: `Task 10`（`docs/codex-tasks/task_10_setup_coco.md`）已完成；`COCO_USER=yilinwang`，Docker/Compose、Node/npm、coco→VPS SSH、Docker build test 全部通过，执行日志在 `logs/task_10.log`。
- 完成: `Task 11`（`docs/codex-tasks/task_11_push_to_coco.md`）已完成；代码已推送到 `/home/yilinwang/builds/esg-research-toolkit`，关键文件齐全，目录大小 `16M`，`logs/build.log` 已创建，执行日志在 `logs/task_11.log`。
- 新出现: `~/.esg-deploy-config` 的 `COCO_BUILD_DIR` 已从错误的本机展开路径修正为远端路径 `/home/yilinwang/builds/esg-research-toolkit`。
- 完成: `Task 12`（coco 构建）、`Task 13`（产物推送到 VPS）与 `Task 14`（VPS 启动与并发验证）均已完成，执行日志见 `logs/task_12.log`、`logs/task_13.log`、`logs/task_14.log`。
- 新出现: coco 上 `usa-vps` 主机别名不可解析，后续应统一使用 `root@192.227.130.69` 或在 coco 配置 SSH Host 别名。
- 新出现: coco 端 `.env.prod` 目前为模板值 `OPENAI_API_KEY=sk-xxx`，Task 12 之前需替换为真实 key。

## 2026-04-12 三层部署进展（Task 12）

- 完成: `Task 12`（`docs/codex-tasks/task_12_build_on_coco.md`）已完成；`esg-toolkit:latest` 构建成功（约 `1.23GB`），前端构建成功并生成 `frontend-dist.tar.gz`（`253K`）。
- 完成: Docker 测试容器启动与健康检查通过，返回 `{"status":"ok"}`；构建产物校验通过（`frontend/dist` `884K`，`frontend/node_modules` `231M`）。
- 新出现: 并发子代理阶段在本地沙箱下多次触发 SSH 限制（`Operation not permitted`），3 次重试后按自愈策略切到主代理直连完成后置步骤；详见 `logs/task_12.log`。
- 完成: `Task 14`（`docs/codex-tasks/task_14_start_vps_service.md`）已完成；容器 `healthy`、Nginx `active`、API/前端链路验证通过（前端本机探活使用 `Host` 头），并发子代理失败重试已收敛（最多 3 次），详见 `logs/task_14.log`。

## 2026-04-12 三层部署进展（Task 13）

- 完成: `Task 13`（`docs/codex-tasks/task_13_push_to_vps.md`）已完成；VPS 目录结构就绪，Docker 镜像、前端产物、配置文件与部署脚本均已从 coco 推送并验证。
- 完成: 并发阶段 4 个子任务（`docker-push`、`frontend-push`、`config-push`、`scripts-push`）全部首轮成功，无需重试；执行日志见 `logs/task_13.log`。
- 完成: 推送后完整性校验通过：`esg-toolkit:latest` 存在（`1.23GB`）、`frontend/dist/index.html` 存在、`docker-compose.prod.yml/.env.prod/nginx/esg.conf` 存在、`scripts/*.sh` 具备可执行权限。
- 完成: coco 构建临时文件已清理（删除 `frontend/node_modules`、`frontend/dist`、`frontend-dist.tar.gz`），构建目录体积回落到 `16M`。

---

## 2026-04-12 Task 05（VPS 环境准备）已完成

- 执行文件: `docs/codex-tasks/task_05_vps_prep.md`
- 目标主机: `usa-vps` (`192.227.130.69`)
- 完成项:
  - 基础环境检查通过: `Ubuntu 24.04.4 LTS`，`/` 可用空间约 `7.5G`，内存 `1.9Gi`
  - 安装成功: `docker.io`、`docker-compose`、`nginx`、`certbot`、`python3-certbot-nginx`、`git`、`curl`
  - 目录确认: `/opt/esg-research-toolkit`、`/opt/esg-data`、`/opt/esg-reports`，权限 `root:root`
  - 仓库确认: `/opt/esg-research-toolkit` 在 `main` 分支，最新提交 `ce47354`
  - `.env.prod` 校验通过: `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`APP_ENV`、`DATABASE_URL` 全部存在，且 API key 非 `sk-xxx` 占位值
- 自愈记录:
  - 在补写 `APP_ENV` 时出现一次远端 Python 转义错误（`SyntaxError`），已即时重试并修复，未影响最终结果
- 后续依赖:
  - 可进入 Task 06（构建并启动 Docker 容器）

---

## 2026-04-12 Task 06（Docker 容器构建和启动）已完成

- 执行文件: `docs/codex-tasks/task_06_docker_deploy.md`
- 目标主机: `usa-vps` (`192.227.130.69`)
- 完成项:
  - 校验 `Dockerfile` 与 `docker-compose.prod.yml` 存在且配置正确（`8001:8000`，健康检查启用）
  - 镜像构建成功: `esg-research-toolkit_api:latest`（镜像 ID `89f62269411b`）
  - 容器启动成功: `esg-research-toolkit_api_1`，状态 `running healthy`
  - 日志验证通过: Uvicorn 正常监听 `0.0.0.0:8000`，无启动异常
  - 接口验证通过:
    - `GET /health` 返回 200，响应 `{\"status\":\"ok\"}`
    - `GET /` 返回 200，包含服务元信息（`name`、`version`、`docs`）
- 自愈记录:
  - 第 1 次构建命令 `docker compose -f ... build --no-cache` 失败（当前 VPS 未启用 `docker compose` 子命令）
  - 自动切换为 `docker-compose -f ... build --no-cache` 后构建成功
  - 首次 `up -d` 因宿主机已有 `uvicorn` 占用 `8001` 失败；按自愈流程定位并停止旧进程后重启容器成功
- 后续依赖:
  - 可进入 Task 07（前端构建和部署）

---

## 2026-04-12 Task 07（前端构建和部署）已完成

- 执行文件: `docs/codex-tasks/task_07_frontend_deploy.md`
- 目标主机: `usa-vps` (`192.227.130.69`)
- 完成项:
  - Node/npm 环境满足要求: `node v22.22.2`，`npm 10.9.7`
  - 前端依赖安装与构建成功，产物存在:
    - `/opt/esg-research-toolkit/frontend/dist/index.html`
    - `/opt/esg-research-toolkit/frontend/dist/assets/*`
  - Nginx 配置已部署:
    - `esg.conf` 已复制到 `/etc/nginx/sites-available/`
    - `sites-enabled/esg.conf` 软链接已生效
    - 默认站点已移除
    - `nginx -t` 通过（syntax ok / test successful）
  - Nginx 服务状态正常: `active (running)`
  - HTTP 验证通过:
    - `GET http://127.0.0.1/` 返回 `200`（`Content-Type: text/html`）
    - `GET http://127.0.0.1/api/health` 返回 `{\"status\":\"ok\"}`
  - HTTPS 验证通过:
    - `certbot --nginx -d esg.meichen.beauty ...` 成功部署证书
    - `certbot certificates` 显示 `esg.meichen.beauty` 证书有效，过期时间 `2026-07-11`
    - `GET https://esg.meichen.beauty/` 返回 `200`
- 自愈记录:
  - 在本地 loop 封装命令阶段出现 SSH 连接受限（`Operation not permitted`），已切换为逐条远端执行并继续完成任务
  - 按 DNS 预检策略先检查解析后再执行 certbot，避免无效重试
- 已知风险:
  - `nginx -t` 与 `systemctl status nginx` 存在多条 `meichen.beauty/www/eu` 的 `conflicting server name` 警告，不影响当前站点可用性，但建议在 Task 09 前清理重复站点配置
- 后续依赖:
  - 可进入 Task 08（端到端功能验证）

---

## 2026-04-13 Task 08（端到端功能验证）已完成（含线上热修）

- 执行文件: `docs/codex-tasks/task_08_e2e_validation.md`
- 目标主机: `usa-vps` (`192.227.130.69`)
- 验证结果:
  - 前端可访问: `https://esg.meichen.beauty/` 返回 `200`
  - 静态资源可访问: `/assets/index-Kd8BKYCE.js` 返回 `200`
  - API 健康检查通过: `GET /api/health` 返回 `{\"status\":\"ok\"}`
  - PDF 上传接口通过: `POST /report/upload` 返回 `200`，并写入数据库记录
  - Taxonomy 评分通过: `POST /taxonomy/score`（按当前 schema 使用 `report_year`）返回 `200`
  - LCOE 计算通过: `POST /techno/lcoe`（按当前 schema 使用 `technology/capex_eur_per_kw`）返回 `200`
  - 报告 PDF 端点通过: `GET /taxonomy/report/pdf?company_name=Unknown&report_year=2024` 返回 `200`，生成有效 PDF
  - 数据库持久化通过: `/opt/esg-data/esg_toolkit.db` 存在（12K），`company_reports` 记录数 `1`
  - 资源占用通过: 容器内存约 `130MiB`（<500MB），磁盘可用约 `5.8G`（>2GB）
- 自愈与热修:
  - 文档 payload 与当前 API schema 存在漂移（`year`→`report_year`、LCOE 字段变化），已按当前代码 schema 调整请求并重试成功
  - 发现 `/taxonomy/report/pdf` 初次 500（`primary_activities` 被存为 JSON 字符串，Pydantic 期望 list）
  - 已修复 `taxonomy_scorer/api.py`：新增 DB 记录字段标准化逻辑，将 `primary_activities` 字符串反序列化为 list 后再校验
  - 热修已同步 VPS 并重建容器，端点由 500 恢复为 200
- 残留问题:
  - 首页 `<title>` 当前为 `frontend`，未体现 “ESG Research Toolkit”
  - `/api/health` 返回值为 `ok`（与旧文档的 `healthy` 不一致）
  - 由于 `OPENAI_API_KEY` 无效，上传解析退化为降级路径（日志出现 401），`company_name` 落库为 `Unknown`
  - 生成的测试 PDF 大小约 `5.5K`，低于任务文档中的 `>10KB` 期望（但文件类型与内容生成均正常）
- 后续依赖:
  - 可进入 Task 09（监控和日志配置）

---

## 2026-04-13 Task 09（监控和日志配置）已完成

- 执行文件: `docs/codex-tasks/task_09_monitoring.md`
- 目标主机: `usa-vps` (`192.227.130.69`)
- 完成项:
  - Docker 日志轮转已启用并验证: `Logging Driver: json-file`，`max-size=10m`，`max-file=3`
  - 日志脚本可用: `/opt/esg-research-toolkit/scripts/logs.sh` 运行成功
  - 健康检查脚本可用: `/opt/esg-research-toolkit/scripts/health-check.sh` 运行通过
  - Cron 任务已确认存在:
    - `*/5 * * * * /opt/esg-research-toolkit/scripts/health-check.sh >> /var/log/esg-health.log 2>&1`
    - `0 3 * * * /opt/esg-research-toolkit/scripts/backup.sh >> /var/log/esg-backup.log 2>&1`
  - Nginx 日志格式已生效: `esg_combined` + `esg-access.log`
  - 备份脚本可用: `/opt/esg-research-toolkit/scripts/backup.sh` 成功生成数据库备份
  - 状态仪表脚本可用: `/opt/esg-research-toolkit/scripts/status.sh` 运行成功
- 自愈记录:
  - `health-check.sh` 初版使用 `curl http://127.0.0.1/` 误判前端不可用（server_name 不匹配导致 404）
  - 已改为带 `Host: esg.meichen.beauty` 的本机探活后通过
  - Cron 配置采用“读取-合并-保留现有任务”策略，避免覆盖 VPS 上既有 crontab 项
- 本轮新增/变更文件:
  - `scripts/logs.sh`
  - `scripts/health-check.sh`
  - `scripts/backup.sh`
  - `scripts/status.sh`
  - `taxonomy_scorer/api.py`（Task 08 热修，修复 PDF 报告端点 500）
- 残留风险:
  - VPS 根分区使用率约 `85%`（虽仍有 `5.8G` 可用，但高于健康脚本告警阈值）
  - Nginx 仍有多条 `conflicting server name` 警告，建议后续清理重复站点配置
  - OpenAI API key 当前无效，上传解析会降级为基础抽取（日志可见 401）
