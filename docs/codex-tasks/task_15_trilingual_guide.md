# Task 15: 三语言使用指南（EN / ZH / DE）

**目标**: 生成三份完整的 GitHub README，覆盖英文 / 中文 / 德文，内容从代码自动提取，始终与实现保持同步。

**优先级**: P1

**预计时间**: 30–45 分钟（Codex loop 自动执行）

**输出文件**:
- `README.md` （英文，主文件）
- `README.zh.md`（中文）
- `README.de.md`（德文）

---

## 自愈策略

每步执行后运行验证点。失败时按"自愈动作"重试最多 3 次，仍失败则记录错误继续下一步。

---

## Step 1 — 读取项目现状（信息收集，只读）

```bash
# 1-A 读取 API 端点列表
python3 -c "
import sys; sys.path.insert(0,'.')
from main import app
routes = [(r.methods, r.path) for r in app.routes if hasattr(r,'methods')]
for m,p in sorted(routes, key=lambda x: x[1]):
    print(list(m)[0] if m else 'GET', p)
"

# 1-B 读取前端页面列表
ls frontend/src/pages/

# 1-C 读取框架说明
python3 -c "
from main import app
from fastapi.testclient import TestClient
c = TestClient(app)
import json
print(json.dumps(c.get('/frameworks/list').json(), ensure_ascii=False, indent=2))
"

# 1-D 读取 requirements 依赖
cat requirements.txt

# 1-E 读取 docker-compose 端口
grep -E 'ports:|image:|service' docker-compose.yml 2>/dev/null || echo 'no docker-compose.yml'
```

**验证点**: 以上命令均无报错，输出非空。

---

## Step 2 — 生成 README.md（英文主文件）

写入 `README.md`，内容结构如下（根据 Step 1 的实际信息填充）：

```
# ESG Research Toolkit

> Open-source platform for corporate ESG report analysis, EU Taxonomy compliance scoring,
> multi-framework comparison (EU Taxonomy · CSRC 2023 · CSRD/ESRS), and renewable energy
> techno-economic analysis (LCOE/NPV/IRR).

[badges: Python 3.12+ | FastAPI | React 18 | License MIT | Live Demo]

## ✨ Features
（列出 8 项核心功能，每项一行，带 emoji）

## 🚀 Quick Start

### Prerequisites
- Python 3.12+, Node 18+, Docker (optional)

### Local Development
（3 步启动：clone → pip install → uvicorn 和 npm dev）

### Docker
（docker-compose up 一键启动）

## 📡 API Reference
（表格：Method | Endpoint | Description，从 Step 1-A 自动填充）

## 🏗 Architecture
（简单文字图：Frontend → Nginx → FastAPI → SQLite）

## 🌍 Multi-Framework ESG
（说明三框架：EU Taxonomy / CSRC 2023 / CSRD，各两句话）

## 📊 Frontend Pages
（从 Step 1-B 列出 7 页面，每页一句描述）

## 🔧 Configuration
（.env 变量说明表格）

## 🤝 Contributing
（标准 Fork → PR 流程）

## 📄 License
MIT
```

**验证点**:
```bash
wc -l README.md   # 应 >= 100 行
grep "Quick Start" README.md
grep "API Reference" README.md
```

---

## Step 3 — 生成 README.zh.md（中文版）

将 README.md 的所有内容翻译为简体中文，保持 Markdown 结构完全相同：
- 所有章节标题翻译为中文
- 代码块保持原样（不翻译命令）
- 技术术语（FastAPI、Docker、ESG）保持英文原词
- Badge 行保持不变
- 三框架名称格式：`EU Taxonomy 2020 · 中国证监会 CSRC 2023 · 欧盟 CSRD/ESRS`

**验证点**:
```bash
wc -l README.zh.md   # 应 >= 100 行
grep "快速开始\|快速启动\|开始使用" README.zh.md
python3 -c "open('README.zh.md').read().encode('utf-8')"  # 无编码错误
```

---

## Step 4 — 生成 README.de.md（德文版）

将 README.md 的所有内容翻译为德文，保持 Markdown 结构完全相同：
- 所有章节标题翻译为德文
- 代码块保持原样
- 技术术语（FastAPI、Docker、ESG）保持英文原词
- 三框架名称格式：`EU-Taxonomie 2020 · China CSRC 2023 · EU CSRD/ESRS`
- 使用正式德文（Sie-Form 而不是 du-Form）

**验证点**:
```bash
wc -l README.de.md   # 应 >= 100 行
grep -i "schnellstart\|Schnellstart\|Erste Schritte" README.de.md
```

---

## Step 5 — 语言切换徽章（互相链接）

在三个文件的顶部（第一行之后，第一个段落之前）插入语言切换行：

**README.md** 插入：
```markdown
🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)
```

**README.zh.md** 插入：
```markdown
🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)
```

**README.de.md** 插入：
```markdown
🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)
```

**验证点**:
```bash
grep "README.md.*README.zh.md.*README.de.md" README.md
grep "README.md.*README.zh.md.*README.de.md" README.zh.md
grep "README.md.*README.zh.md.*README.de.md" README.de.md
```

---

## Step 6 — 一致性检查

```bash
# 章节数量对比（三文件应相同 ±1）
echo "EN: $(grep '^## ' README.md | wc -l) sections"
echo "ZH: $(grep '^## ' README.zh.md | wc -l) sections"
echo "DE: $(grep '^## ' README.de.md | wc -l) sections"

# API 表格行数对比
echo "EN API rows: $(grep -c '|' README.md)"
echo "ZH API rows: $(grep -c '|' README.zh.md)"
echo "DE API rows: $(grep -c '|' README.de.md)"
```

**自愈动作**: 如果 ZH 或 DE 的章节数比 EN 少 2 个以上，重新生成对应文件。

---

## Step 7 — Commit & Push

```bash
git add README.md README.zh.md README.de.md
git status

git commit -m "docs: add trilingual README (EN/ZH/DE) with auto-extracted API reference

- README.md: English main guide
- README.zh.md: 简体中文版本
- README.de.md: Deutsche Version
- Language switcher badges cross-linked in all three files
- API reference auto-extracted from FastAPI routes
- Multi-framework section covers EU Taxonomy / CSRC 2023 / CSRD"

git push origin HEAD
```

**验证点**:
```bash
git log --oneline -1 | grep "trilingual\|README"
```

---

## 完成标准

- [ ] `README.md` 存在，>= 100 行，含 Quick Start + API Reference
- [ ] `README.zh.md` 存在，>= 100 行，中文无乱码
- [ ] `README.de.md` 存在，>= 100 行，德文章节标题正确
- [ ] 三文件均含语言切换徽章
- [ ] 已 commit 并 push

---

## 执行指令（直接传给 Codex）

```
在 ~/projects/esg-research-toolkit 目录执行 docs/codex-tasks/task_15_trilingual_guide.md。
使用自愈 loop 模式：每步完成后运行验证点，失败则自愈重试（最多 3 次），全部通过后继续下一步。
完成后输出每个步骤的状态（✓/✗）和最终三文件的行数统计。
```
