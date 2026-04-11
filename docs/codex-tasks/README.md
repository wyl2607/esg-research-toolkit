# Codex 自动化开发总指南

**项目**: ESG Research Toolkit  
**GitHub**: https://github.com/wyl2607/esg-research-toolkit  
**当前版本**: v0.1.0  
**目标**: 让 Codex 独立完成剩余任务，支持 loop 运行和自愈

---

## 快速开始

### 1. 查看任务清单
```bash
cat docs/codex-tasks/TASK_LIST.md
```

### 2. 执行单个任务
```bash
codex exec \
  --prompt "$(cat docs/codex-tasks/task_01_user_guide.md)"
```

### 3. Loop 自动执行所有任务
```bash
# 在项目根目录执行
./scripts/codex_loop.sh
```

---

## 项目当前状态

### ✅ 已完成（v0.1.0）
- 3 个核心模块：report_parser, taxonomy_scorer, techno_economics
- 15 个 API 端点（FastAPI）
- 19 个测试（100% 通过）
- GitHub 发布
- 三语言 README（英文、中文、德文）

### 📋 待完成任务（按优先级）
1. **Task 1**: 三语言用户手册（高优先级）
2. **Task 2**: 模块联动集成（高优先级）
3. **Task 3**: Docker 部署（中优先级）
4. **Task 4**: CI/CD pipeline（中优先级）
5. **Task 5**: 前端界面（低优先级，可选）

---

## 文件结构

```
docs/codex-tasks/
├── TASK_LIST.md              # 任务总览
├── task_01_user_guide.md     # Task 1: 用户手册
├── task_02_integration.md    # Task 2: 模块联动
├── task_03_docker.md         # Task 3: Docker
├── task_04_cicd.md           # Task 4: CI/CD
└── task_05_frontend.md       # Task 5: 前端（可选）

scripts/
├── codex_loop.sh             # Loop 自动执行脚本
└── verify_task.sh            # 任务验证脚本
```

---

## 核心原则

### 1. 第一性原理
所有功能必须直接服务于企业 ESG 分析。不做无关功能。

### 2. 自愈机制
- 每个任务执行后自动验证
- 失败时自动分析错误并重试（最多 3 次）
- 记录错误日志到 `logs/codex_errors.log`

### 3. 模块联动
三个模块的协同工作流程：
```
PDF 上传 → ESG 数据提取 → Taxonomy 评分 → LCOE 分析 → 综合报告
   ↓            ↓              ↓             ↓           ↓
report_parser  analyzer    taxonomy_scorer  techno    reporter
```

### 4. 验证标准
每个任务完成后必须通过：
- 代码语法检查（python -m py_compile）
- 单元测试（pytest）
- 集成测试（端到端工作流）
- 文档完整性检查

---

## 使用 Codex 的最佳实践

### 1. 模型选择
- 复杂任务：`gpt-5.4`
- 简单任务：`gpt-5.4-mini`
- 文档翻译：`gpt-5.4`

### 2. Approval Policy
- 开发阶段：`on-failure`（失败时才需要人工确认）
- 生产部署：`on-request`（每次都确认）

### 3. 上下文管理
每个任务文件都包含：
- 任务目标
- 输入/输出
- 验证标准
- 自愈规则
- 参考文件路径

---

## 下一步

1. 阅读 `docs/codex-tasks/TASK_LIST.md` 了解所有任务
2. 从 Task 1 开始执行
3. 每完成一个任务，更新 `PROJECT_PROGRESS.md`
4. 遇到问题查看 `logs/codex_errors.log`

---

## 联系方式

- GitHub Issues: https://github.com/wyl2607/esg-research-toolkit/issues
- 项目维护者: wyl2607@gmail.com
