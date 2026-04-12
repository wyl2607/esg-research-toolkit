"""PDF report generator for EU Taxonomy analysis using reportlab."""
from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
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


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"],
            fontSize=22, textColor=INDIGO, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontSize=10, textColor=SLATE, spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"],
            fontSize=13, textColor=BLACK, spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, textColor=BLACK, leading=14,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"],
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
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
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
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
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
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
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
