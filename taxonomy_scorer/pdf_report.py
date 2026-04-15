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
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
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

_CJK_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Songti.ttc", "Songti"),
    ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK"),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "WQYZenHei"),
]
_CJK_FONT_NAME = "Helvetica"


def _register_cjk_font() -> str:
    """Register first available CJK font and return font name."""
    global _CJK_FONT_NAME
    for path, name in _CJK_FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            _CJK_FONT_NAME = name
            return name
        except Exception:
            continue
    return _CJK_FONT_NAME


_register_cjk_font()


class _ChartFlowable(Flowable):
    """Render a Drawing object inside platypus story."""

    def __init__(self, drawing: Drawing):
        super().__init__()
        self.drawing = drawing

    def wrap(self, *_args: object) -> tuple[float, float]:  # type: ignore[override]
        return self.drawing.width, self.drawing.height

    def draw(self) -> None:  # type: ignore[override]
        renderPDF.draw(self.drawing, self.canv, 0, 0)


def _make_scope_bar_chart(
    scope1: float | None,
    scope2: float | None,
    scope3: float | None,
    width: float = 14 * cm,
    height: float = 6 * cm,
) -> Drawing:
    """Create Scope 1/2/3 emissions bar chart as reportlab Drawing."""
    d = Drawing(width, height)
    values = [
        ("Scope 1", float(scope1 or 0), "#ef4444"),
        ("Scope 2", float(scope2 or 0), "#f97316"),
        ("Scope 3", float(scope3 or 0), "#6366f1"),
    ]

    max_val = max((value for _, value, _ in values), default=1.0) or 1.0
    bar_w = width / 5
    gap = bar_w * 0.3
    chart_h = height - (1.6 * cm)
    y_base = 1 * cm

    for idx, (label, value, color_hex) in enumerate(values):
        x = gap + idx * (bar_w + gap)
        bar_h = (value / max_val) * chart_h if max_val else 0
        d.add(
            Rect(
                x,
                y_base,
                bar_w,
                bar_h,
                fillColor=colors.HexColor(color_hex),
                strokeColor=None,
            )
        )
        d.add(
            String(
                x + bar_w / 2,
                y_base - 0.35 * cm,
                label,
                textAnchor="middle",
                fontSize=8,
                fontName=_CJK_FONT_NAME,
            )
        )
        if value > 0:
            val_str = f"{value / 1000:.1f}k" if value >= 1000 else f"{value:.0f}"
            d.add(
                String(
                    x + bar_w / 2,
                    y_base + bar_h + 0.08 * cm,
                    val_str,
                    textAnchor="middle",
                    fontSize=7,
                    fontName=_CJK_FONT_NAME,
                )
            )

    d.add(
        Line(
            gap / 2,
            y_base,
            width - gap / 2,
            y_base,
            strokeColor=colors.HexColor("#94a3b8"),
        )
    )
    d.add(
        String(
            width / 2,
            height - 0.25 * cm,
            "GHG Emissions by Scope (tCO₂e)",
            textAnchor="middle",
            fontSize=9,
            fontName=_CJK_FONT_NAME,
        )
    )
    return d


def _make_objective_radar_chart(
    objective_scores: dict[str, float],
    width: float = 14 * cm,
    height: float = 8 * cm,
) -> Drawing:
    """Create a simple radar-style polygon chart for objective scores."""
    d = Drawing(width, height)
    objective_keys = [
        "climate_mitigation",
        "climate_adaptation",
        "water",
        "circular_economy",
        "pollution_prevention",
        "biodiversity",
    ]
    labels = [OBJECTIVE_LABELS.get(k, k.replace("_", " ").title()) for k in objective_keys]
    values = [max(0.0, min(1.0, float(objective_scores.get(k, 0.0)))) for k in objective_keys]

    center_x = width / 2
    center_y = height / 2
    radius = min(width, height) * 0.34
    levels = [0.25, 0.5, 0.75, 1.0]

    def _point(angle_deg: float, r: float) -> tuple[float, float]:
        import math

        rad = math.radians(angle_deg)
        return center_x + r * math.cos(rad), center_y + r * math.sin(rad)

    count = len(values)
    angle_step = 360 / count
    start_angle = 90.0

    for level in levels:
        ring_points: list[float] = []
        for idx in range(count):
            px, py = _point(start_angle - idx * angle_step, radius * level)
            ring_points.extend([px, py])
        d.add(
            Polygon(
                ring_points,
                fillColor=None,
                strokeColor=colors.HexColor("#cbd5e1"),
                strokeWidth=0.8,
            )
        )

    score_points: list[float] = []
    for idx, value in enumerate(values):
        axis_angle = start_angle - idx * angle_step
        ax_x, ax_y = _point(axis_angle, radius)
        d.add(Line(center_x, center_y, ax_x, ax_y, strokeColor=colors.HexColor("#94a3b8")))

        label_x, label_y = _point(axis_angle, radius * 1.18)
        d.add(
            String(
                label_x,
                label_y,
                labels[idx],
                fontName=_CJK_FONT_NAME,
                fontSize=7,
                textAnchor="middle",
            )
        )

        sc_x, sc_y = _point(axis_angle, radius * value)
        score_points.extend([sc_x, sc_y])
    d.add(
        Polygon(
            score_points,
            fillColor=colors.HexColor("#6366f1AA"),
            strokeColor=colors.HexColor("#4338ca"),
            strokeWidth=1.2,
        )
    )
    d.add(
        String(
            width / 2,
            height - 0.25 * cm,
            "Environmental Objective Radar",
            textAnchor="middle",
            fontSize=9,
            fontName=_CJK_FONT_NAME,
        )
    )
    return d


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
        ("FONTNAME",     (0, 0), (-1, 0), _CJK_FONT_NAME),
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
        ("FONTNAME",     (0, 0), (-1, 0), _CJK_FONT_NAME),
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
    story.append(Spacer(1, 0.5 * cm))
    story.append(_ChartFlowable(_make_objective_radar_chart(result.objective_scores)))
    story.append(Spacer(1, 14))

    # ── ESG Data ──────────────────────────────────────────────────────────
    story.append(Paragraph("Key ESG Metrics", s["h2"]))
    metrics = [
        ("Scope 1 Emissions", f"{data.scope1_co2e_tonnes:,.0f} t CO₂e" if data.scope1_co2e_tonnes else "—"),
        ("Scope 2 Emissions", f"{data.scope2_co2e_tonnes:,.0f} t CO₂e" if data.scope2_co2e_tonnes else "—"),
        ("Scope 3 Emissions", f"{data.scope3_co2e_tonnes:,.0f} t CO₂e" if data.scope3_co2e_tonnes else "—"),
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
        ("FONTNAME",     (0, 0), (-1, 0), _CJK_FONT_NAME),
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
    chart = _make_scope_bar_chart(
        data.scope1_co2e_tonnes,
        data.scope2_co2e_tonnes,
        data.scope3_co2e_tonnes,
    )
    story.append(Spacer(1, 0.5 * cm))
    story.append(_ChartFlowable(chart))
    story.append(Spacer(1, 14))

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
