# Task 1: 三语言用户手册

**优先级**: 高  
**预计时间**: 2-3 小时  
**依赖**: 无

---

## 目标

创建三语言版本的用户手册，让不同语言的用户都能快速上手。

## 输出文件

- `docs/USER_GUIDE.md` — 英文
- `docs/USER_GUIDE.zh.md` — 中文
- `docs/USER_GUIDE.de.md` — 德文

## 内容结构（每个语言版本相同）

```
1. 安装指南
   - 系统要求（Python 3.11+）
   - 克隆仓库
   - 安装依赖（pip install -r requirements.txt）
   - 配置 .env（OPENAI_API_KEY）

2. 快速开始
   - 启动服务器（uvicorn main:app --reload）
   - 访问 API 文档（http://localhost:8000/docs）
   - 健康检查（curl http://localhost:8000/health）

3. 模块使用指南

   3.1 Report Parser（企业报告解析）
   - 功能说明
   - POST /report/upload — 上传 PDF
     - curl 示例
     - Python requests 示例
     - 返回值说明（CompanyESGData）
   - GET /report/companies — 查询所有报告
   - GET /report/companies/{name}/{year} — 查询特定报告

   3.2 Taxonomy Scorer（EU Taxonomy 评分）
   - 功能说明（6 个环保目标 + DNSH）
   - POST /taxonomy/score — 评分
     - curl 示例（使用 examples/mock_esg_data.json）
     - Python requests 示例
     - 返回值说明（TaxonomyScoreResult）
   - POST /taxonomy/report — 生成 JSON 报告
   - POST /taxonomy/report/text — 生成文本报告
   - GET /taxonomy/activities — 支持的活动列表

   3.3 Techno Economics（技术经济分析）
   - 功能说明（LCOE/NPV/IRR）
   - POST /techno/lcoe — LCOE 计算
     - curl 示例（solar PV 案例）
     - Python requests 示例
     - 返回值说明（LCOEResult）
   - POST /techno/sensitivity — 敏感性分析
   - GET /techno/benchmarks — 行业基准数据

4. 端到端工作流
   - 完整案例：GreenTech Solutions GmbH
   - Step 1: 上传 PDF（或使用 mock 数据）
   - Step 2: EU Taxonomy 评分
   - Step 3: LCOE 分析
   - Step 4: 生成综合报告

5. 故障排查
   - 服务器无法启动 → 检查端口 8000 是否被占用
   - OpenAI API 错误 → 检查 .env 中的 OPENAI_API_KEY
   - PDF 解析失败 → 确认 PDF 不是扫描版（需要文字层）
   - 数据库错误 → 删除 esg_toolkit.db 重新初始化

6. 常见问题（FAQ）
   - Q: 支持哪些 PDF 格式？
   - Q: 如何处理中文 PDF？
   - Q: EU Taxonomy 评分的准确性如何？
   - Q: LCOE 计算使用什么公式？
```

## 代码示例参考

### curl 示例（Report Parser）
```bash
# 上传 PDF
curl -X POST http://localhost:8000/report/upload \
  -F "file=@examples/company_report.pdf"

# 查询报告
curl http://localhost:8000/report/companies
```

### Python 示例（Taxonomy Scorer）
```python
import requests

esg_data = {
    "company_name": "GreenTech Solutions GmbH",
    "report_year": 2024,
    "scope1_co2e_tonnes": 1200,
    "renewable_energy_pct": 85,
    "primary_activities": ["solar_pv", "wind_onshore"]
}

response = requests.post(
    "http://localhost:8000/taxonomy/score",
    json=esg_data
)
result = response.json()
print(f"Revenue aligned: {result['revenue_aligned_pct']:.1f}%")
print(f"DNSH pass: {result['dnsh_pass']}")
```

### curl 示例（Techno Economics）
```bash
curl -X POST http://localhost:8000/techno/lcoe \
  -H "Content-Type: application/json" \
  -d '{
    "technology": "solar_pv",
    "capex_eur_per_kw": 800,
    "opex_eur_per_kw_year": 15,
    "capacity_factor": 0.18,
    "lifetime_years": 25,
    "discount_rate": 0.07
  }'
```

## 验证标准

- [ ] 三个文件都已创建
- [ ] 每个 API 端点都有 curl 和 Python 示例
- [ ] 代码示例语法正确（可直接复制运行）
- [ ] 技术术语准确（LCOE, DNSH, TSC 等）
- [ ] 德文翻译符合技术文档规范

## 自愈规则

1. 如果 API 端点不存在，检查 `main.py` 和各模块 `api.py`，使用正确的端点
2. 如果代码示例有语法错误，自动修复
3. 如果翻译不准确，重新生成该语言版本
4. 如果文件创建失败，检查目录是否存在（mkdir -p docs/）

## 参考文件

- `main.py` — 查看所有注册的路由
- `report_parser/api.py` — Report Parser 端点
- `taxonomy_scorer/api.py` — Taxonomy Scorer 端点
- `techno_economics/api.py` — Techno Economics 端点
- `core/schemas.py` — 数据模型定义
- `PROJECT_PROGRESS.md` — 项目状态

## Codex 执行命令

```bash
codex --model gpt-5.4 --approval-policy on-failure \
  --prompt "读取 docs/codex-tasks/task_01_user_guide.md，按照规格创建三语言用户手册（docs/USER_GUIDE.md 英文、docs/USER_GUIDE.zh.md 中文、docs/USER_GUIDE.de.md 德文）。先读取 main.py 和各模块 api.py 了解实际端点，确保代码示例可运行。"
```
