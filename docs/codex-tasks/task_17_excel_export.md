# Task 17: Excel/CSV 数据导出

**目标**: 为 Companies 页面和 Taxonomy 页面添加一键导出 Excel/CSV 功能。

**优先级**: P2

**预计时间**: 1–2 小时

---

## Step 1 — 安装依赖

```bash
source .venv/bin/activate
pip install openpyxl~=3.1.0
echo "openpyxl~=3.1.0" >> requirements.txt
python3 -c "import openpyxl; print('openpyxl', openpyxl.__version__)"
```

---

## Step 2 — 后端：添加导出端点

在 `report_parser/api.py` 中添加：

```python
from fastapi.responses import StreamingResponse
import io, csv, openpyxl

@router.get("/companies/export/csv")
def export_companies_csv(db: Session = Depends(get_db)):
    """导出所有公司数据为 CSV。"""
    records = list_reports(db, skip=0, limit=10000)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        'company_name','report_year','scope1_co2e_tonnes','scope2_co2e_tonnes',
        'scope3_co2e_tonnes','energy_consumption_mwh','renewable_energy_pct',
        'water_usage_m3','waste_recycled_pct','total_employees','female_pct',
    ])
    writer.writeheader()
    for r in records:
        writer.writerow({f: getattr(r, f, None) for f in writer.fieldnames})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="esg_companies.csv"'},
    )

@router.get("/companies/export/xlsx")
def export_companies_xlsx(db: Session = Depends(get_db)):
    """导出所有公司数据为 Excel。"""
    records = list_reports(db, skip=0, limit=10000)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ESG Data"
    headers = [
        'Company','Year','Scope1 (tCO2e)','Scope2 (tCO2e)','Scope3 (tCO2e)',
        'Energy (MWh)','Renewable %','Water (m³)','Waste Recycled %',
        'Employees','Female %',
    ]
    ws.append(headers)
    for r in records:
        ws.append([
            r.company_name, r.report_year,
            r.scope1_co2e_tonnes, r.scope2_co2e_tonnes, r.scope3_co2e_tonnes,
            r.energy_consumption_mwh, r.renewable_energy_pct,
            r.water_usage_m3, r.waste_recycled_pct,
            r.total_employees, r.female_pct,
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="esg_companies.xlsx"'},
    )
```

**验证点**:
```bash
source .venv/bin/activate
uvicorn main:app --port 8000 &
sleep 2
curl -sf "http://localhost:8000/report/companies/export/csv" | head -3
curl -sf "http://localhost:8000/report/companies/export/xlsx" -o /tmp/test.xlsx && python3 -c "import openpyxl; wb=openpyxl.load_workbook('/tmp/test.xlsx'); print('rows:', wb.active.max_row)"
```

---

## Step 3 — 前端：CompaniesPage 加导出按钮

在 `frontend/src/pages/CompaniesPage.tsx` 的工具栏区域添加两个按钮：

```tsx
<Button variant="outline" size="sm" onClick={() => window.open('/api/report/companies/export/csv')}>
  <Download size={14} className="mr-1" /> CSV
</Button>
<Button variant="outline" size="sm" onClick={() => window.open('/api/report/companies/export/xlsx')}>
  <Download size={14} className="mr-1" /> Excel
</Button>
```

**验证点**:
```bash
cd frontend && npm run build 2>&1 | tail -5
```

---

## Step 4 — 测试

```bash
pytest tests/ -q 2>&1 | tail -3
```

---

## Step 5 — Commit & Push

```bash
git add report_parser/api.py frontend/src/pages/CompaniesPage.tsx requirements.txt
git commit -m "feat: Excel/CSV export for companies data"
git push origin HEAD
```

---

## 完成标准

- [ ] `GET /report/companies/export/csv` 返回有效 CSV
- [ ] `GET /report/companies/export/xlsx` 返回有效 Excel
- [ ] 前端 Companies 页面有 CSV/Excel 下载按钮
- [ ] 所有测试通过
- [ ] 已 commit push

---

## 执行指令（传给 Codex）

```
在 ~/projects/esg-research-toolkit 执行 docs/codex-tasks/task_17_excel_export.md。
自愈 loop 模式。先安装 openpyxl，再加端点，再加前端按钮，最后 commit push。
```
