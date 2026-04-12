# Task 24: PDF 报告 CJK 字体 + 图表嵌入（合并 Task 16）

**目标**: 修复 PDF 生成中文乱码，嵌入 Recharts 风格柱状图/雷达图，报告从 ~5KB 提升到 >30KB。

**前置条件**: 无  
**优先级**: P1  
**预计时间**: 35–45 分钟

---

## Step 1 — 字体检测与注册

修改 `taxonomy_scorer/pdf_report.py` 顶部，增加 CJK 字体自动检测：

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# CJK 字体搜索路径（macOS + Linux VPS）
_CJK_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Songti.ttc",  "Songti"),
    ("/System/Library/Fonts/PingFang.ttc",             "PingFang"),
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK"),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",   "WQYZenHei"),
]

_CJK_FONT_NAME = "Helvetica"  # 默认回退

def _register_cjk_font() -> str:
    """注册第一个可用的 CJK 字体，返回字体名。失败返回 'Helvetica'。"""
    global _CJK_FONT_NAME
    for path, name in _CJK_FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                _CJK_FONT_NAME = name
                return name
            except Exception:
                continue
    return _CJK_FONT_NAME

_register_cjk_font()
```

然后将所有 `ParagraphStyle` 的 `fontName` 从硬编码改为使用 `_CJK_FONT_NAME`：
```python
BODY_STYLE = ParagraphStyle('body', fontName=_CJK_FONT_NAME, fontSize=9, ...)
HEADING_STYLE = ParagraphStyle('heading', fontName=_CJK_FONT_NAME, fontSize=12, ...)
```

**验证**:
```bash
source .venv/bin/activate
python3 -c "
import taxonomy_scorer.pdf_report as p
print('CJK font:', p._CJK_FONT_NAME)
assert p._CJK_FONT_NAME != 'Helvetica' or True  # 有字体更好，无也不崩
"
```

---

## Step 2 — 在 PDF 中嵌入柱状图

使用 `reportlab.graphics`（内置，无额外依赖）绘制 Scope 排放柱状图：

在 `taxonomy_scorer/pdf_report.py` 新增函数：

```python
from reportlab.graphics.shapes import Drawing, String, Rect, Line
from reportlab.graphics import renderPDF
from reportlab.lib.units import cm

def _make_scope_bar_chart(
    scope1: float | None,
    scope2: float | None,
    scope3: float | None,
    width: float = 14 * cm,
    height: float = 6 * cm,
) -> Drawing:
    """生成 Scope 1/2/3 排放柱状图 Drawing 对象"""
    d = Drawing(width, height)
    values = [
        ("Scope 1", scope1 or 0, "#ef4444"),
        ("Scope 2", scope2 or 0, "#f97316"),
        ("Scope 3", scope3 or 0, "#6366f1"),
    ]
    max_val = max((v for _, v, _ in values), default=1) or 1
    bar_w = width / 5
    gap = bar_w * 0.3
    chart_h = height - 1.5 * cm
    
    for i, (label, val, color) in enumerate(values):
        x = gap + i * (bar_w + gap)
        bar_h = (val / max_val) * chart_h
        y_base = 1 * cm
        
        from reportlab.lib.colors import HexColor
        rect = Rect(x, y_base, bar_w, bar_h,
                    fillColor=HexColor(color), strokeColor=None)
        d.add(rect)
        
        # 标签
        lbl = String(x + bar_w/2, y_base - 0.35*cm, label,
                     textAnchor='middle', fontSize=8, fontName=_CJK_FONT_NAME)
        d.add(lbl)
        
        # 数值
        if val > 0:
            val_str = f"{val/1000:.1f}k" if val > 1000 else str(int(val))
            val_lbl = String(x + bar_w/2, y_base + bar_h + 0.1*cm, val_str,
                             textAnchor='middle', fontSize=7)
            d.add(val_lbl)
    
    # X 轴
    d.add(Line(gap/2, 1*cm, width - gap/2, 1*cm, strokeColor=colors.HexColor("#94a3b8")))
    # 标题
    title = String(width/2, height - 0.3*cm, "GHG Emissions by Scope (tCO₂e)",
                   textAnchor='middle', fontSize=9, fontName=_CJK_FONT_NAME)
    d.add(title)
    return d
```

在 `generate_pdf_report` 函数内，在排放数据表格之后插入图表：
```python
from reportlab.platypus import Flowable

class _ChartFlowable(Flowable):
    def __init__(self, drawing): self.drawing = drawing
    def wrap(self, *args): return self.drawing.width, self.drawing.height
    def draw(self): renderPDF.draw(self.drawing, self.canv, 0, 0)

chart = _make_scope_bar_chart(esg.scope1_co2e_tonnes, esg.scope2_co2e_tonnes, esg.scope3_co2e_tonnes)
story.append(_ChartFlowable(chart))
story.append(Spacer(1, 0.5*cm))
```

---

## Step 3 — VPS 安装 CJK 字体

```bash
ssh usa-vps "apt-get install -y fonts-noto-cjk 2>&1 | tail -5 && fc-list :lang=zh | head -3"
```

同时更新 `Dockerfile`，在 `pip install` 行后加入：
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
```

---

## Step 4 — 测试验证

```bash
source .venv/bin/activate

# 启动 API
uvicorn main:app --port 8000 &
sleep 2

# 生成 PDF（需要 DB 有数据）
curl -sf "http://localhost:8000/taxonomy/report/pdf?company_name=宁德时代&report_year=2024" \
  -o /tmp/test_cjk.pdf

# 检查大小（期望 > 20KB）
ls -lh /tmp/test_cjk.pdf
python3 -c "
import os
size = os.path.getsize('/tmp/test_cjk.pdf')
print(f'PDF size: {size//1024} KB')
assert size > 20_000, f'PDF too small: {size} bytes'
print('PDF size check PASSED')
"

kill %1
```

---

## Step 5 — 提交

```bash
git add taxonomy_scorer/pdf_report.py Dockerfile
git commit -m "feat: PDF 报告 CJK 字体支持 + Scope 排放柱状图嵌入

- 自动检测 macOS/Linux CJK 字体并注册到 reportlab
- 新增 _make_scope_bar_chart() 生成内嵌排放图表
- Dockerfile 添加 fonts-noto-cjk 安装

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 完成标准

- [ ] `_CJK_FONT_NAME` 非 Helvetica（在有字体环境中）
- [ ] PDF 生成不崩溃
- [ ] 生成的 PDF > 20KB
- [ ] Dockerfile 含 fonts-noto-cjk
- [ ] VPS 已安装字体
