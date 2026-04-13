from core.schemas import CompanyESGData
from taxonomy_scorer.gap_analyzer import analyze_gaps
from taxonomy_scorer.pdf_report import generate_pdf
from taxonomy_scorer.scorer import score_company


def test_generate_pdf_with_chinese_company_name() -> None:
    data = CompanyESGData(
        company_name="宁德时代 CATL",
        report_year=2024,
        scope1_co2e_tonnes=93440.0,
        scope2_co2e_tonnes=12500.0,
        renewable_energy_pct=45.0,
        total_employees=98000,
        primary_activities=["battery_storage"],
    )

    result = score_company(data)
    gaps = analyze_gaps(data, result)
    pdf = generate_pdf(data, result, gaps)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 5000
