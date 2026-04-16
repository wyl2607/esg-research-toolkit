# 🇩🇪 German Demo Seed — 操作手册

> **目的**：把 `german_demo_manifest.json` 里的德国 demo 报告批量灌进数据库，让 BenchmarkPage / PeerComparisonCard 在 demo 时有真实的多公司、多年份数据可看。
>
> **执行者**：你（人工 + 终端）
>
> **当前 scope**：manifest 现有 **36** 条 seed 记录，覆盖 **2022 / 2023 / 2024** 多年份。
>
> **总耗时**：第一次约 1–2 小时（取决于还剩多少 URL 需要人工校验和补 PDF）。重跑通常 15–30 分钟。
>
> **模型说明**：抽取模型跟随后端当前 `OPENAI_MODEL` 配置；只有 `--validate` / `--validate-only` 的 Phase B 校验仍固定使用 `gpt-4o-mini`。

---

## 📋 前置检查清单（开始前 5 分钟）

| 项目 | 怎么验证 | 期望 |
|---|---|---|
| 在项目根目录 | `pwd` | `/Users/yumei/projects/esg-research-toolkit` |
| Python venv 存在 | `ls .venv/bin/python` | 文件存在 |
| 后端依赖装好 | `.venv/bin/pip show openai httpx fastapi` | 三个都有版本号 |
| OpenAI 余额 | 打开 https://platform.openai.com/usage | 至少 $30 |
| 真实 API key | `echo $OPENAI_API_KEY \| head -c 8` | 显示 `sk-proj-` 或 `sk-` 开头 |
| 30G + 30H + 30I 已合并 | `git log --oneline -10` | 看到 30G/30H/30I 提交 |
| 端口 8000 空闲 | `lsof -i :8000` | 没有输出 |
| 8GB 磁盘空间 | `df -h .` | Available > 8GB（多年份 PDF 缓存会比旧版更大） |

**如果有任意一项失败，先停下解决，不要继续往下。**

---

## STEP 1 —— 校验 manifest 里仍标记 `verify: true` 的 URL（约 10–30 分钟）

### 1.1 打开 manifest

**文件**：`scripts/seed_data/german_demo_manifest.json`

**工具**：你的编辑器（VS Code / Cursor / 任何）

**做什么**：
- manifest 现在是多年份列表，不是旧版 10 家/2024-only 清单
- 只有还标着 `verify: true` 的条目需要优先人工确认
- 你的任务：**逐个把这些 URL 粘到浏览器**，看它是不是真的能下到 PDF

### 1.2 三种结果对应三种处理

| URL 结果 | 处理 |
|---|---|
| ✅ **直接下到 PDF**（浏览器开始下载，或显示 PDF 预览） | 把 manifest 里这一项的 `"verify": true` 改成 `"verify": false`。**URL 不用动**。 |
| 🟡 **跳到一个落地页，需要再点一下"下载"** | 在落地页右键复制真正的 PDF 链接，**替换 manifest 里的 `source_url`**，然后 `"verify": false`。 |
| ❌ **404 / 403 / 链接死掉** | 走 [STEP 1.3](#13-死链兜底手动放-pdf) 兜底方案。 |

### 1.3 死链兜底：手动放 PDF

**这是脚本设计就预期会发生的情况**——别紧张。

1. 在 Google 搜：`<公司名> sustainability report 2024 PDF` 或 `<公司名> annual report 2024 site:<公司域名>`
2. 找到任意一份 2024 年的可持续/年度报告 PDF，下载到本地
3. 把 PDF 重命名为 manifest 里那个公司的 `slug` + `.pdf`
   - 例：RWE 那条 `slug` 是 `rwe-2024` → 文件名 `rwe-2024.pdf`
4. **放进这个目录**：`scripts/seed_data/pdfs/`
   - 完整路径示例：`/Users/yumei/projects/esg-research-toolkit/scripts/seed_data/pdfs/rwe-2024.pdf`
5. manifest 里这一项的 `source_url` 不用改（脚本会先看本地缓存，本地有就不下载了），`verify` 改成 `false`

**验证 PDF 有效**：
```bash
ls -lh scripts/seed_data/pdfs/rwe-2024.pdf
# 期望：文件大小 > 1MB（小于 1KB 脚本会拒绝）
```

### 1.4 完成校验后

理想状态是 manifest 里所有待跑条目都已经 `verify: false`，或者你至少把这次要跑的条目都确认过了。

如果还有少数条目死活找不到 PDF，可以先不跑那几条，或者临时从 manifest 删掉；但要保住你想 demo 的行业样本。最实用的最小集合是：

- `D35.11` 至少 3 条，方便电力同行分位数展示
- `C29.10` 保留多年份，方便车企历史切换
- `C20.14` 或 `J61.10` 至少保留 1 个多年份公司，方便演示 history

---

## STEP 2 —— 启动后端（一个 terminal 长开）

### 2.1 开新 terminal #1

```bash
cd /Users/yumei/projects/esg-research-toolkit
export OPENAI_API_KEY=<把你真实的 key 粘这里，sk-proj-... 开头>
.venv/bin/uvicorn main:app --port 8000 --host 127.0.0.1
```

### 2.2 期望输出

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Started server process [...]
INFO:     Application startup complete.
```

### 2.3 烟测一下后端真的起来了

**开 terminal #2**（保持 #1 不动）：

```bash
curl -s http://127.0.0.1:8000/benchmarks/D35.11
```

期望返回：`{"industry_code":"D35.11","metrics":[]}` 或同结构空结果（空数组很正常，因为现在还没 seed）。

**如果这一步就 500 了，停下，查 terminal #1 的报错。** 不要往下跑 seed。

---

## STEP 3 —— 跑 seed（terminal #2，10–20 分钟）

### 3.1 先 dry-run 确认无网络版本能跑

```bash
cd /Users/yumei/projects/esg-research-toolkit
.venv/bin/python scripts/seed_german_demo.py --dry-run
```

期望输出：
- `loaded 36 companies from german_demo_manifest.json`（数字以 manifest 当前实际条目数为准）
- 每家公司一行 `[dry-run] would download ...`
- 末尾 `Phase A summary: {"succeeded": [...], "failed": [], ...}`

**如果这里报错（manifest 解析失败、import 失败），停下修。** 真跑的时候会更脆弱。

### 3.2 真跑 Phase A + Phase B

```bash
.venv/bin/python scripts/seed_german_demo.py --validate
```

**这一步会发生什么**：

| 阶段 | 看到啥 | 用时 |
|---|---|---|
| 加载 manifest | `loaded N companies` | 1 秒 |
| 对每家公司 | `→ <name> ... downloading ... uploading ... ✅ extracted` | 约 1–2 分钟/家 |
| Phase A 末尾 | `triggering benchmark recompute... ✅ recomputed: {"industries": N, "metric_rows": M}` | 几秒 |
| Phase B 启动 | `running Phase B sanity checks for N companies...` | 即时 |
| 每家校验 | `✅ <name>: clean` 或 `⚠️  <name>: K concern(s)` | 5–10 秒/家 |
| 末尾 | `📝 anomalies report written to scripts/seed_data/anomalies_report.md` | 即时 |

**总耗时**：约 15–25 分钟。**别关 terminal**，别 Ctrl+C。

### 3.3 常见失败 + 处理

| 报错 | 含义 | 处理 |
|---|---|---|
| `❌ upload failed: 422` | 后端不接受 form 字段 | 检查 30E 是否真的合并了；`grep -n "industry_code" report_parser/api.py` |
| `❌ upload failed: 500` | extractor 内部炸了 | 看 terminal #1 的 traceback；通常是 PDF 太大或损坏，换 PDF |
| `⚠️  download failed (status=404)` | URL 死了 | 回 [STEP 1.3](#13-死链兜底手动放-pdf) 手动放 PDF，再重跑（脚本有缓存，只会重处理失败的那家） |
| `⚠️  <name>: openai: ...` | Phase B OpenAI 调用失败 | 不阻塞，继续；末尾 `anomalies_report.md` 会标出来 |
| Phase B 整个跳过 | `OPENAI_API_KEY not set` | 你忘了 export，回 STEP 2.1 |

### 3.4 重跑策略（很重要）

脚本是 **idempotent** 的：

- 已经成功 seed 进去的 **同公司 / 同年份** 记录，下次跑会自动 `↺ already seeded, skipping`
- 失败的公司可以单独修了 PDF / URL 再重跑
- 想从零开始：`.venv/bin/python scripts/seed_german_demo.py --reset`（按 manifest 删除对应的公司年份组合）然后重跑

---

## STEP 4 —— 人工 spot-check（约 10 分钟）

### 4.1 看异常报告

**文件**：`scripts/seed_data/anomalies_report.md`

**用什么打开**：你的编辑器，或 `cat scripts/seed_data/anomalies_report.md`

**怎么看**：
- 如果是 `_No anomalies flagged. All extracted records passed the sanity check._` → 撒花，跳过 4.2
- 如果有 `## <公司名>` 区块 → 每个 `⚠️` 条目都要人工判断

**判断流程**：
1. 看 concern 里说的 metric 和 value
2. 打开本地 PDF：`open scripts/seed_data/pdfs/<slug>.pdf`
3. 用 PDF 搜索那个数字，看抽取是不是真的错了
4. 三种结果：
   - **抽取错了** → 打开浏览器 `http://localhost:5173/manual` → 用 ManualCaseBuilderPage 手动覆盖那一家公司
   - **AI 误报** → 不管它
   - **PDF 本身就有问题**（例如错印了一个零） → 在报告里加注释，demo 时主动说

### 4.2 看真实 benchmark 数据

**操作**：

1. **开 terminal #3**（前两个保持不动）
2. ```bash
   cd /Users/yumei/projects/esg-research-toolkit/frontend
   npm run dev
   ```
3. 浏览器打开 http://localhost:5173/benchmarks
4. 行业下拉先选 **D35.11 — Electricity production**
5. 期望看到：
   - 几个有数字的 percentile 行（scope1/scope2/energy 等）
   - 下面 "Contributing companies" 列出 RWE / EnBW / Uniper 等（取决于你 seed 成功了几家、哪个年份有数据）
6. 如果页面有年份切换，分别点一下 `2024 / 2023 / 2022`，确认多年份 benchmark 都能切换
7. 再切到 **C24.10 — Basic iron and steel** 或 **C29.10 — Motor vehicles**，确认至少还有一个行业非空

### 4.3 看单公司 peer card

1. 浏览器打开 http://localhost:5173/companies
2. 点任意一家 seed 公司（比如 RWE AG 或 Volkswagen AG）
3. 滚到 "Peer comparison — Electricity production (D35.11)" 卡片
4. 期望看到：
   - 几行 metric，每行有 Company value / Industry p50 / Position bucket
   - bucket 标签可能是 `p25–p50` / `above p90` 之类
5. 如果这家公司有多年份 history，再切换年份确认 profile / peer card 不只停在 2024
6. **这就是 demo 的核心 30 秒**

---

## STEP 5 —— 演示前最终检查清单

跑完上面之后，确认这些都成立才算 demo-ready：

| 检查项 | 怎么验证 | 期望 |
|---|---|---|
| `/benchmarks` 至少 3 个行业有数据 | 浏览器切下拉 | 至少 3 个行业非空，且最好覆盖 2022 / 2023 / 2024 |
| 至少一家公司的 Peer card 有 ≥ 4 个 metric 行 | 打开 RWE profile 看 Peer 卡 | 表格至少 4 行 |
| Peer card 里有 evidence 链路 | 滚到下面看 evidence_summary | 有 page references |
| `/benchmarks` 的 "Recompute benchmarks" 按钮可用 | 点一下 | 出现 "Updated N industries" 绿提示 |
| 异常报告已审完 | `cat scripts/seed_data/anomalies_report.md` | 没有未处理的 ⚠️ |
| 后端没崩 | 看 terminal #1 | 没有 ERROR / Traceback |
| 把上面所有数据用德语界面再看一遍 | 浏览器右上语言切到 DE | 标签都是 "Branchenbenchmarks" / "Peer-Vergleich" |

---

## 🔥 如果某天 demo 前要重置一切

**完全干净重来**：

```bash
# 1. 停掉前后端（Ctrl+C terminal #1 和 #3）
# 2. 删 SQLite
rm -f esg.db reports.db   # 不确定文件名就 ls *.db
# 3. 删 PDF 缓存（可选；不删的话脚本会优先复用本地 PDF）
# rm -rf scripts/seed_data/pdfs/*.pdf
# 4. 重启后端
OPENAI_API_KEY=<real> .venv/bin/uvicorn main:app --port 8000
# 5. 重新 seed
.venv/bin/python scripts/seed_german_demo.py --validate
```

**只重置 seed 公司，保留其它数据**：

```bash
.venv/bin/python scripts/seed_german_demo.py --reset
.venv/bin/python scripts/seed_german_demo.py --validate
```

---

## 📞 故障速查

| 症状 | 第一步查哪里 |
|---|---|
| BenchmarkPage 全空 | 浏览器开 http://127.0.0.1:8000/benchmarks/D35.11 看是不是真的有数据；如果有 → 前端 query 问题；如果没有 → seed 没跑成功 |
| Peer card 显示 "No NACE industry code" | 该公司 seed 时 `industry_code` 没存进去；检查 manifest 里那条记录 |
| Phase B 一直 timeout | OpenAI 限流或响应慢；改成 `--validate-only` 重跑，或只保留这次要 demo 的 manifest 子集 |
| 第二天再跑发现一切都没了 | SQLite 在 git 之外，可能被 `git clean` 误删了；按"完全干净重来"重跑 |
| `npm run dev` 起不来 | 5173 端口被占；`lsof -i :5173` 看是谁；`kill -9 <pid>` |

---

## ✅ 完成标志

跑完整套手册之后，你应该能在 **30 秒** 内向任何人 demo 这个故事：

> "这是 RWE AG 的 ESG profile。看这张 Peer comparison 卡片——RWE 的 Scope 1 排放量在德国电力同行里落在某个分位区间。这些数字不是我编的，每个都能回溯到公司自己的报告 evidence。更关键的是，这里不只是一年快照：我可以切 2022 / 2023 / 2024，看同一家公司和同一行业的变化。所有这些公司的数据都会流进 `/benchmarks` 这张行业 percentile 表；新增任何一家公司或年份，只要 seed 进去再点 Recompute，同业对比就会更新。"

如果你能流畅说完这一段并现场点出来每一步，T12 就完成了，你可以开始写简历了。
