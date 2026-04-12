# Task 16: PDF 报告中文字体支持

**目标**: 修复生成的 PDF 报告中中文显示乱码问题，并将报告大小从 ~5KB 提升到 >20KB（含图表）。

**优先级**: P1

**预计时间**: 20–30 分钟

---

## Step 1 — 检测当前问题

```bash
# 启动本地 API
source .venv/bin/activate
uvicorn main:app --port 8000 &
sleep 2

# 生成测试 PDF
curl -sf "http://localhost:8000/taxonomy/report/pdf?company_name=宁德时代&report_year=2024" \
  -o /tmp/test_zh.pdf 2>&1 || echo "需要先有数据"

# 检查系统字体
fc-list :lang=zh | head -5 2>/dev/null || echo "无 CJK 字体"
ls /usr/share/fonts/truetype/noto/ 2>/dev/null || echo "无 Noto 字体"
python3 -c "from reportlab.pdfbase import pdfmetrics; print('reportlab ok')"
```

**验证点**: 了解当前字体状态

---

## Step 2 — 安装 CJK 字体（VPS 端）

```bash
# 本地检查（macOS 通常已有）
python3 -c "
import os
font_paths = [
    '/System/Library/Fonts/PingFang.ttc',  # macOS
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',  # Linux
    '/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf',
]
for p in font_paths:
    if os.path.exists(p):
        print(f'Found: {p}')
        break
else:
    print('No CJK font found locally')
"
```

---

## Step 3 — 修改 taxonomy_scorer/pdf_report.py

在 `generate_pdf()` 函数中：

1. 注册 CJK 字体：
```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def _register_cjk_font() -> str:
    """注册 CJK 字体，返回字体名称。找不到时退回 Helvetica。"""
    candidates = [
        ('/System/Library/Fonts/PingFang.ttc', 'PingFang', 'PingFang'),
        ('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', 'NotoSansCJK', 'NotoSansCJK'),
        ('/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf', 'NotoSansCJK', 'NotoSansCJK'),
    ]
    for path, name, _ in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return 'Helvetica'
```

2. 在 `generate_pdf()` 开头调用 `_register_cjk_font()`，将返回值赋给 `cjk_font`。
3. 将所有中文文本的 `fontName` 改为 `cjk_font`。

**验证点**:
```bash
python3 -c "
from taxonomy_scorer.pdf_report import generate_pdf
from core.schemas import CompanyESGData
from taxonomy_scorer.scorer import score_company
from taxonomy_scorer.gap_analyzer import analyze_gaps

data = CompanyESGData(
    company_name='宁德时代 CATL',
    report_year=2024,
    scope1_co2e_tonnes=93440,
    scope2_co2e_tonnes=12500,
    renewable_energy_pct=45,
    total_employees=98000,
    primary_activities=['battery_manufacturing'],
)
r = score_company(data)
g = analyze_gaps(data, r)
pdf = generate_pdf(data, r, g)
print(f'PDF size: {len(pdf)} bytes')
assert len(pdf) > 5000, 'PDF too small'
print('✓ PDF generated successfully')
"
```

---

## Step 4 — VPS 安装字体

```bash
ssh usa-vps "
apt-get install -y fonts-noto-cjk 2>/dev/null || apt-get install -y fonts-noto 2>/dev/null
fc-cache -fv
fc-list :lang=zh | head -3
"
```

---

## Step 5 — 重建 VPS 容器

```bash
ssh usa-vps "
cd /opt/esg-research-toolkit
git pull origin main
docker-compose -f docker-compose.prod.yml build --no-cache api
docker-compose -f docker-compose.prod.yml up -d
sleep 5
curl -sf http://127.0.0.1/api/health -H 'Host: esg.meichen.beauty'
"
```

---

## 完成标准

- [ ] `_register_cjk_font()` 函数在 pdf_report.py 中存在
- [ ] 本地生成含中文名称的 PDF，大小 > 5KB，无乱码（目视检查）
- [ ] VPS 已安装 Noto CJK 字体
- [ ] VPS 容器重建成功

---

## 执行指令（传给 Codex）

```
在 ~/projects/esg-research-toolkit 执行 docs/codex-tasks/task_16_pdf_chinese_font.md。
自愈 loop 模式，每步验证通过后继续。macOS 优先用 PingFang.ttc，Linux 用 Noto CJK。
```
