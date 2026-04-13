"""PDF report generator for EU Taxonomy analysis using reportlab."""
from __future__ import annotations

import io
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Flowable, HRFlowable, KeepTogether,
)

from core.schemas import CompanyESGData, TaxonomyScoreResult
from taxonomy_scorer.gap_analyzer import GapItem

# ── Colour palette ──────────────────────────────────────────────────────────
GREEN  = colors.HexColor("#22c55e")
RED    = colors.HexColor("#ef4444")
INDIGO = colors.HexColor("#6366f1")
SLATE  = colors.HexColor("#64748b")
LIGHT  = colors.HexColor("#f1f5f9")
WHITE  = colors.white
BLACK  = colors.HexColor("#0f172a")

SEVERITY_COLOR = {
    "critical": colors.HexColor("#ef4444"),
    "high":     colors.HexColor("#f97316"),
    "medium":   colors.HexColor("#eab308"),
    "low":      colors.HexColor("#22c55e"),
}

OBJECTIVE_LABELS = {
    "climate_mitigation":    "Climate Mitigation",
    "climate_adaptation":    "Climate Adaptation",
    "water":                 "Water & Marine Resources",
    "circular_economy":      "Circular Economy",
    "pollution_prevention":  "Pollution Prevention",
    "biodiversity":          "Biodiversity",
}

# CJK font search paths (macOS + Linux)
_CJK_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Songti.ttc", "Songti"),
    ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK"),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "WQYZenHei"),
]

_CJK_FONT_NAME = "Helvetica"


def _register_cjk_font() -> str:
    """Register the first available CJK font, fallback to Helvetica."""
    global _CJK_FONT_NAME
    for font_path, font_name in _CJK_FONT_CANDIDATES:
        if not os.path.exists(font_path):
            continue
        try:
            if font_path.endswith(".ttc"):
                for idx in range(6):
                    try:
                        candidate = f"{font_name}_{idx}"
                        pdfmetrics.registerFont(TTFont(candidate, font_path, subfontIndex=idx))
                        _CJK_FONT_NAME = candidate
                        return _CJK_FONT_NAME
                    except Exception:
                        continue
            else:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                _CJK_FONT_NAME = font_name
                return _CJK_FONT_NAME
        except Exception:
            continue
    for cid_name in ("STSong-Light", "HeiseiMin-W3"):
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(cid_name))
            _CJK_FONT_NAME = cid_name
            return _CJK_FONT_NAME
        except Exception:
            continue
    return _CJK_FONT_NAME


_register_cjk_font()


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"],
            fontName=_CJK_FONT_NAME,
            fontSize=22, textColor=INDIGO, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontName=_CJK_FONT_NAME,
            fontSize=10, textColor=SLATE, spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"],
            fontName=_CJK_FONT_NAME,
            fontSize=13, textColor=BLACK, spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontName=_CJK_FONT_NAME,
            fontSize=9, textColor=BLACK, leading=14,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"],
            fontName=_CJK_FONT_NAME,
            fontSize=8, textColor=SLATE, leading=12,
        ),
    }


def _make_scope_bar_chart(
    scope1: float | None,
    scope2: float | None,
    scope3: float | None,
    width: float = 14 * cm,
    height: float = 6 * cm,
) -> Drawing:
    """Build a Scope 1/2/3 emissions bar chart as a reportlab Drawing."""
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

        rect = Rect(
            x,
            y_base,
            bar_w,
            bar_h,
            fillColor=colors.HexColor(color),
            strokeColor=None,
        )
        d.add(rect)

        lbl = String(
            x + bar_w / 2,
            y_base - 0.35 * cm,
            label,
            textAnchor="middle",
            fontSize=8,
            fontName=_CJK_FONT_NAME,
        )
        d.add(lbl)

        if val > 0:
            val_str = f"{val/1000:.1f}k" if val > 1000 else str(int(val))
            val_lbl = String(
                x + bar_w / 2,
                y_base + bar_h + 0.1 * cm,
                val_str,
                textAnchor="middle",
                fontSize=7,
                fontName=_CJK_FONT_NAME,
            )
            d.add(val_lbl)

    d.add(Line(gap / 2, 1 * cm, width - gap / 2, 1 * cm, strokeColor=colors.HexColor("#94a3b8")))
    title = String(
        width / 2,
        height - 0.3 * cm,
        "GHG Emissions by Scope (tCO2e)",
        textAnchor="middle",
        fontSize=9,
        fontName=_CJK_FONT_NAME,
    )
    d.add(title)
    return d


class _ChartFlowable(Flowable):
    def __init__(self, drawing: Drawing):
        super().__init__()
        self.drawing = drawing

    def wrap(self, *_):
        return self.drawing.width, self.drawing.height

    def draw(self):
        renderPDF.draw(self.drawing, self.canv, 0, 0)


def _progress_bar(score: float, width: float = 180, height: float = 10) -> Table:
    """Render a horizontal progress bar as a tiny Table."""
    fill = max(0.0, min(1.0, score))
    filled_w = fill * width
    empty_w  = (1 - fill) * width
    bar_color = GREEN if fill >= 0.6 else (colors.HexColor("#f97316") if fill >= 0.3 else RED)

    data = [[""  , ""]]
    col_widths = [filled_w, empty_w] if filled_w > 0 else [0.01, width]
    t = Table(data, colWidths=col_widths, rowHeights=[height])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), bar_color),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ("ROUNDEDCORNERS", [5]),
    ]))
    return t


def generate_pdf(
    data: CompanyESGData,
    result: TaxonomyScoreResult,
    gaps: list[GapItem],
) -> bytes:
    """Return PDF bytes for a full EU Taxonomy report."""
    buf = io.BytesIO()
    cjk_font = _CJK_FONT_NAME
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        pageCompression=0,
    )
    s = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────
    story.append(Paragraph("EU Taxonomy Alignment Report", s["title"]))
    story.append(Paragraph(
        f"{data.company_name} &nbsp;·&nbsp; FY {data.report_year} &nbsp;·&nbsp; "
        f"Generated {date.today().isoformat()}",
        s["subtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=INDIGO, spaceAfter=10))

    # ── Summary KPIs ──────────────────────────────────────────────────────
    story.append(Paragraph("Alignment Summary", s["h2"]))
    dnsh_text = "<font color='#22c55e'>✓ PASS</font>" if result.dnsh_pass \
        else "<font color='#ef4444'>✗ FAIL</font>"

    kpi_data = [
        ["Metric", "Value"],
        ["Revenue Aligned",  f"{result.revenue_aligned_pct:.1f}%"],
        ["CapEx Aligned",    f"{result.capex_aligned_pct:.1f}%"],
        ["OpEx Aligned",     f"{result.opex_aligned_pct:.1f}%"],
        ["DNSH Status",      Paragraph(dnsh_text, s["body"])],
    ]
    kpi_table = Table(kpi_data, colWidths=[8*cm, 8*cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), INDIGO),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), cjk_font),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("BACKGROUND",   (0, 1), (-1, -1), LIGHT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("ALIGN",        (1, 0), (1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # ── Objective Scores ──────────────────────────────────────────────────
    story.append(Paragraph("Environmental Objective Scores", s["h2"]))
    obj_rows = [["Objective", "Score", "Progress"]]
    for key, score in result.objective_scores.items():
        label = OBJECTIVE_LABELS.get(key, key.replace("_", " ").title())
        obj_rows.append([
            Paragraph(label, s["body"]),
            Paragraph(f"<b>{score:.0%}</b>", s["body"]),
            _progress_bar(score),
        ])
    obj_table = Table(obj_rows, colWidths=[7*cm, 2.5*cm, 6*cm])
    obj_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), INDIGO),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), cjk_font),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ALIGN",        (1, 0), (1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(obj_table)
    story.append(Spacer(1, 14))

    # ── ESG Data ──────────────────────────────────────────────────────────
    story.append(Paragraph("Key ESG Metrics", s["h2"]))
    metrics = [
        ("Scope 1 Emissions", f"{data.scope1_co2e_tonnes:,.0f} t CO₂e" if data.scope1_co2e_tonnes else "—"),
        ("Scope 2 Emissions", f"{data.scope2_co2e_tonnes:,.0f} t CO₂e" if data.scope2_co2e_tonnes else "—"),
        ("Renewable Energy",  f"{data.renewable_energy_pct:.1f}%" if data.renewable_energy_pct else "—"),
        ("Water Consumption", f"{data.water_usage_m3:,.0f} m³" if data.water_usage_m3 else "—"),
        ("Waste Recycled",    f"{data.waste_recycled_pct:.1f}%" if data.waste_recycled_pct else "—"),
        ("Total Employees",   f"{data.total_employees:,}" if data.total_employees else "—"),
        ("Female Ratio",      f"{data.female_pct:.1f}%" if data.female_pct else "—"),
        ("Primary Activities", ", ".join(data.primary_activities) or "—"),
    ]
    met_data = [["Metric", "Value"]] + metrics
    met_table = Table(met_data, colWidths=[8*cm, 8*cm])
    met_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), SLATE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), cjk_font),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(met_table)
    story.append(Spacer(1, 14))

    chart = _make_scope_bar_chart(
        data.scope1_co2e_tonnes,
        data.scope2_co2e_tonnes,
        data.scope3_co2e_tonnes,
    )
    story.append(_ChartFlowable(chart))
    story.append(Spacer(1, 0.5 * cm))

    # ── Gaps ──────────────────────────────────────────────────────────────
    if gaps:
        story.append(Paragraph(f"Compliance Gaps ({len(gaps)} identified)", s["h2"]))
        for gap in gaps:
            sev_color = SEVERITY_COLOR.get(gap.severity, SLATE)
            block = KeepTogether([
                Table(
                    [[
                        Paragraph(f"<b>{gap.severity.upper()}</b>", s["small"]),
                        Paragraph(f"<b>{OBJECTIVE_LABELS.get(gap.objective, gap.objective)}</b>", s["body"]),
                    ]],
                    colWidths=[2.5*cm, 13*cm],
                    style=TableStyle([
                        ("BACKGROUND",   (0, 0), (0, 0), sev_color),
                        ("TEXTCOLOR",    (0, 0), (0, 0), WHITE),
                        ("ALIGN",        (0, 0), (0, 0), "CENTER"),
                        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING",   (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
                        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                        ("BACKGROUND",   (1, 0), (1, 0), LIGHT),
                    ]),
                ),
                Table(
                    [
                        [Paragraph(gap.description, s["body"])],
                        [Paragraph(f"→ {gap.action}", s["small"])],
                    ],
                    colWidths=[15.5*cm],
                    style=TableStyle([
                        ("BACKGROUND",   (0, 0), (-1, -1), WHITE),
                        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
                        ("TOPPADDING",   (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
                        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ]),
                ),
                Spacer(1, 6),
            ])
            story.append(block)

    # ── Recommendations ───────────────────────────────────────────────────
    if result.recommendations:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Recommendations", s["h2"]))
        for i, rec in enumerate(result.recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", s["body"]))
            story.append(Spacer(1, 4))

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE))
    story.append(Paragraph(
        "Generated by ESG Research Toolkit · https://esg.meichen.beauty · "
        "Based on EU Taxonomy Regulation (2020/852)",
        s["small"],
    ))

    doc.build(story)
    return buf.getvalue()
