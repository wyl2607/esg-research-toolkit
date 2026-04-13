# Repo Sync 分层策略（本地开发 vs GitHub 同步）

> 目标：GitHub 只同步“工具产品相关内容”；本地开发过程产物保留在本地，不上传。

## L1：必须同步到 GitHub（产品层）

- 核心代码：`core/` `report_parser/` `taxonomy_scorer/` `techno_economics/` `frontend/src/`
- 运行与部署：`docker-compose*.yml` `Dockerfile` `nginx/` `scripts/deploy*.sh` 等
- 测试与必要文档：`tests/`、README、用户文档

## L2：可选同步（协作层）

- 与实现直接相关的技术文档（设计说明、接口说明、公开 SOP）
- 仅保留可复用、对协作者有价值的内容

## L3：仅本地保留（开发过程层，不上传）

- 进度/过程记录：`PROJECT_PROGRESS.md` `INCIDENT_LOG.md` `SUMMARY.md`
- 本地安全/审计草稿：`SECURITY.md` `SECURITY_SUMMARY.md`
- 本地工作区产物：`.local/`、`logs/`、`data/`、`.omx/`、`.codex/`、`.claude/`
- 任何密钥、私人配置、临时脚本和实验文件

## 已落地的保护机制

1. `.gitignore` 已忽略 L3 文件与目录。
2. `.guard/local-only-files.txt` 定义本地专用文件白名单（禁止提交）。
3. `.guard/local-prefixes.txt` / `.guard/public-prefixes.txt` 定义目录级分区规则。
4. `scripts/security_check.sh` 会在提交前阻断：
   - 本地专用文件
   - 中转/第三方 API 端点
   - 非官方 `OPENAI_BASE_URL`
5. `scripts/review_push_guard.sh` 用于 push 前复核：

```bash
bash scripts/review_push_guard.sh origin/main
```

6. `scripts/review_file_zones.sh` 用于分层审查（含未分类文件阻断）：

```bash
bash scripts/review_file_zones.sh --staged --block-local
```

7. Git hooks 自动化（一次安装）：

```bash
bash scripts/install_git_guards.sh
```

8. CI 级审核（避免本地绕过）：
   - Workflow: `.github/workflows/repo-guard.yml`
   - 在 PR 和 main push 上执行 `scripts/review_push_guard.sh`

9. 部署可追溯指纹：
   - 写入脚本：`scripts/write_deploy_fingerprint.sh`
   - 远端打点：`scripts/stamp_remote_fingerprint.sh`
   - 默认文件：`/opt/esg-research-toolkit/.deploy-fingerprint.json`

## 处理“已上传但应本地保留”的标准动作

```bash
# 仅取消追踪，不删除本地文件
git rm --cached PROJECT_PROGRESS.md SECURITY.md SECURITY_SUMMARY.md SUMMARY.md

# 提交后推送，GitHub 上将删除这些文件，本地仍保留
```

## 日常提交建议

1. 先执行 `bash scripts/security_check.sh`
2. 再执行 `bash scripts/review_file_zones.sh --staged --block-local`
3. 推送前执行 `bash scripts/review_push_guard.sh origin/main`
4. 全部通过后再 `git push`
