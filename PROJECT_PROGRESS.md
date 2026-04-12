# ESG Research Toolkit — 项目进度报告

**最后更新**: 2026-04-12
**GitHub**: https://github.com/wyl2607/esg-research-toolkit
**状态**: ✅ v0.2.0 前端完成，约 95% 完成度

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
| Stage 8 | 生产部署（VPS） | 🔄 进行中 |

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

- [ ] Stage 8: VPS 生产部署（Docker + Nginx + HTTPS）
