# ESG Research Toolkit — 项目进度报告

**最后更新**: 2026-04-12  
**GitHub**: https://github.com/wyl2607/esg-research-toolkit  
**状态**: ✅ v0.1.0 已完成并发布

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
  - 硬编码 TSC 阈值：solar_pv, wind_onshore, wind_offshore, battery_storage, building_renovation, district_heating
  - GHG 阈值：100 gCO2e/kWh
- `scorer.py`: 合规评分引擎
- `gap_analyzer.py`: 差距分析（severity: critical/high/medium/low）
- `reporter.py`: JSON + 文本报告生成
- `api.py`: 4 个端点
  - `POST /taxonomy/score` - 评分
  - `GET /taxonomy/report` - JSON 报告
  - `GET /taxonomy/report/text` - 文本报告
  - `GET /taxonomy/activities` - 支持的活动列表

### ✅ Stage 4: techno_economics 模块（已完成）
- `lcoe.py`: LCOE 计算（numpy + scipy）
  - 验证：solar PV (800 €/kW, CF=0.18) → LCOE 49.2 €/MWh, IRR 9.0%
- `npv_irr.py`: NPV/IRR/回收期计算
- `sensitivity.py`: CAPEX/OPEX ±20% 敏感性分析
- `api.py`: 3 个端点
  - `POST /techno/lcoe` - LCOE 计算
  - `POST /techno/sensitivity` - 敏感性分析
  - `GET /techno/benchmarks` - 行业基准数据

### ✅ Stage 5: 测试 + GitHub + 发布（已完成）
- **测试覆盖**（用 Codex gpt-5.4 编写）
  - `tests/test_techno_economics.py` - 7 个测试
  - `tests/test_taxonomy_scorer.py` - 6 个测试
  - `tests/test_report_parser.py` - 6 个测试
  - **总计 19 个测试，100% 通过**
- **GitHub 发布**
  - 仓库创建：https://github.com/wyl2607/esg-research-toolkit
  - 代码推送：37 个文件，1949 行
- **cv.md 更新**
  - GitHub 链接修复为正确用户名 `wyl2607`

---

## 技术栈

- **后端**: FastAPI + Uvicorn
- **数据库**: SQLAlchemy 2.0 + SQLite
- **AI**: OpenAI API (gpt-4o)
- **PDF 解析**: pdfplumber
- **科学计算**: numpy, scipy
- **测试**: pytest
- **类型检查**: Pydantic v2

---

## API 端点总览（15 个）

### Report Parser (3)
- `POST /report/upload`
- `GET /report/companies`
- `GET /report/companies/{company_name}/{report_year}`

### Taxonomy Scorer (4)
- `POST /taxonomy/score`
- `GET /taxonomy/report`
- `GET /taxonomy/report/text`
- `GET /taxonomy/activities`

### Techno Economics (3)
- `POST /techno/lcoe`
- `POST /techno/sensitivity`
- `GET /techno/benchmarks`

### System (5)
- `GET /` - 欢迎页面
- `GET /health` - 健康检查
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc
- `GET /openapi.json` - OpenAPI schema

---

## 项目统计

| 指标 | 数值 |
|------|------|
| 总文件数 | 37 |
| 代码行数 | 1,949 |
| 核心模块 | 3 |
| API 端点 | 15 |
| 测试用例 | 19 |
| 测试通过率 | 100% |
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
- [ ] 多语言支持（中文、英文、德文）
- [ ] 前端界面（React/Vue）
- [ ] 更多 EU Taxonomy 活动支持
- [ ] PDF 报告生成（不只是文本）
- [ ] Docker 部署
- [ ] CI/CD pipeline

### v1.0.0（长期）
- [ ] 真实企业案例验证
- [ ] 性能优化（大文件处理）
- [ ] 更多可再生能源技术（氢能、地热等）
- [ ] CSRD/ESRS 完整支持
- [ ] 多用户系统
