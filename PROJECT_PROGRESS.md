# ESG Research Toolkit — 项目进度报告

**最后更新**: 2026-04-12  
**GitHub**: https://github.com/wyl2607/esg-research-toolkit  
**状态**: ✅ v0.1.0 核心功能完成，约 85% 完成度

---

## 完成度概览

| 阶段 | 内容 | 状态 |
|------|------|------|
| Stage 1 | 清理 + 重建 schemas | ✅ 完成 |
| Stage 2 | report_parser 模块 | ✅ 完成 |
| Stage 3 | taxonomy_scorer 模块 | ✅ 完成 |
| Stage 4 | techno_economics 模块 | ✅ 完成 |
| Stage 5 | 测试 + 文档 + Docker + CI/CD | ✅ 完成 |
| Stage 6 | 真实数据验证 | ⬜ 未开始 |
| Stage 7 | 前端界面 | ⬜ 未开始 |
| Stage 8 | 生产部署（VPS） | ⬜ 未开始 |

---

## 项目概览

ESG Research Toolkit 是一个开源的企业 ESG 分析工具，专注于：
1. 企业报告解析（PDF → 结构化 ESG 数据）
2. EU Taxonomy 合规评分（6 个环保目标 + DNSH）
3. 可再生能源项目技术经济分析（LCOE/NPV/IRR）

**第一性原理**: 所有功能直接服务于分析真实企业的 ESG 合规状况和可再生能源项目评估。

---

## 开发进度

### ✅ Stage 1: 清理 + 重建 schemas（已完成）
- 删除 `literature_pipeline/`（违反第一性原理）
- 重写 `core/schemas.py`：`CompanyESGData`, `TaxonomyScoreResult`, `LCOEInput`, `LCOEResult`
- 更新 `main.py`：注册 3 个 router

### ✅ Stage 2: report_parser 模块（已完成）
- `extractor.py`: PDF 文本提取（pdfplumber）
- `analyzer.py`: OpenAI 抽取 ESG 指标
- `storage.py`: SQLAlchemy ORM（CompanyReport 表）
- `api.py`: 3 个端点
  - `POST /report/upload` - 上传 PDF，返回 CompanyESGData
  - `GET /report/companies` - 列出所有公司
  - `GET /report/companies/{company_name}/{report_year}` - 获取特定报告

### ✅ Stage 3: taxonomy_scorer 模块（已完成）
- `framework.py`: EU Taxonomy 规则（6 目标 + DNSH + TSC）
- `scorer.py`: 合规评分引擎
- `gap_analyzer.py`: 差距分析（severity: critical/high/medium/low）
- `reporter.py`: JSON + 文本报告生成
- `api.py`: 4 个端点

### ✅ Stage 4: techno_economics 模块（已完成）
- `lcoe.py`: LCOE 计算（numpy + scipy）
- `npv_irr.py`: NPV/IRR/回收期计算
- `sensitivity.py`: CAPEX/OPEX ±20% 敏感性分析
- `api.py`: 3 个端点

### ✅ Stage 5: 测试 + 文档 + Docker + CI/CD（已完成）
- 19 个测试，100% 通过
- 三语言用户手册（docs/USER_GUIDE.md / .zh.md / .de.md）
- 端到端工作流（workflows/end_to_end.py, batch_analysis.py）
- Mock 数据 + 3 个示例企业（examples/）
- Docker 部署（Dockerfile + docker-compose.yml + .dockerignore）
- GitHub Actions CI/CD（test.yml + lint.yml + docker.yml）
- GitHub 发布：https://github.com/wyl2607/esg-research-toolkit

### ⬜ Stage 6: 真实数据验证（未开始，最高优先级）
- 用真实企业 ESG 报告 PDF 测试 report_parser
- 验证 taxonomy_scorer 评分逻辑是否合理
- 优化 OpenAI prompt 和 EU Taxonomy 规则
- 记录真实案例结果

### ⬜ Stage 7: 前端界面（未开始）
- React/Vue Web UI
- 功能：上传 PDF → 显示提取数据 → 显示评分结果 → 导出报告

### ⬜ Stage 8: 生产部署（未开始）
- 部署到 VPS（USA 或 France）
- 配置域名、HTTPS、监控

---

## 技术栈

- **后端**: FastAPI + Uvicorn
- **数据库**: SQLAlchemy 2.0 + SQLite
- **AI**: OpenAI API (gpt-4o)
- **PDF 解析**: pdfplumber
- **科学计算**: numpy, scipy
- **测试**: pytest（19 个，100% 通过）
- **类型检查**: Pydantic v2
- **部署**: Docker + GitHub Actions

---

## API 端点总览（15 个）

| 模块 | 端点 | 方法 |
|------|------|------|
| Report Parser | `/report/upload` | POST |
| Report Parser | `/report/companies` | GET |
| Report Parser | `/report/companies/{name}/{year}` | GET |
| Taxonomy Scorer | `/taxonomy/score` | POST |
| Taxonomy Scorer | `/taxonomy/report` | POST |
| Taxonomy Scorer | `/taxonomy/report/text` | POST |
| Taxonomy Scorer | `/taxonomy/activities` | GET |
| Techno Economics | `/techno/lcoe` | POST |
| Techno Economics | `/techno/sensitivity` | POST |
| Techno Economics | `/techno/benchmarks` | GET |
| System | `/` | GET |
| System | `/health` | GET |
| System | `/docs` | GET |
| System | `/redoc` | GET |
| System | `/openapi.json` | GET |

---

## 项目统计

| 指标 | 数值 |
|------|------|
| 总 Python 文件 | 26 |
| 核心模块 | 3 |
| API 端点 | 15 |
| 测试用例 | 19 |
| 测试通过率 | 100% |
| 文档语言 | 3（EN/ZH/DE） |
| Python 版本 | 3.11+ |


---

## 核心设计原则

1. **第一性原理**: 只做直接服务于企业 ESG 分析的功能
2. **独立性**: 不依赖 SustainOS 或其他项目
3. **AI 驱动**: 用 OpenAI API（不用 Anthropic）
4. **类型安全**: Pydantic v2 + Python 3.11+ 类型注解
5. **测试优先**: 所有核心功能都有测试覆盖

---

## 已废弃的内容

- `literature_pipeline/` - arXiv 文献抓取（违反第一性原理，已删除）
- `core/claude_client.py` - Anthropic API（已替换为 OpenAI）

---

## Done Criteria（全部完成 ✅）

- ✅ `POST /report/upload` 接受 PDF，返回 `CompanyESGData`
- ✅ `POST /taxonomy/score` 接受 `CompanyESGData`，返回 6 目标对齐度 + DNSH 结果
- ✅ `POST /techno/lcoe` 接受项目参数，返回 LCOE + NPV + IRR
- ✅ pytest 覆盖率 ≥ 70%（实际 100%）
- ✅ 无 `literature_pipeline` 残留
- ✅ GitHub repo 公开，cv.md 链接更新

---

## 下一步计划

### v0.2.0（可选）
- [ ] 前端界面（React/Vue）
- [ ] 更多 EU Taxonomy 活动支持
- [ ] PDF 报告生成（不只是文本）

### v1.0.0（长期）
- [ ] 真实企业案例验证
- [ ] 性能优化（大文件处理）
- [ ] 更多可再生能源技术（氢能、地热等）
- [ ] CSRD/ESRS 完整支持
- [ ] 多用户系统
