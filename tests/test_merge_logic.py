import pytest
from core.schemas import MergeSourceInput, MergePreviewResponse
from report_parser.merge_engine import build_merge_preview

def test_build_merge_preview_includes_framework_versions():
    doc = MergeSourceInput(
        company_name="Test Co",
        report_year=2023,
        source_document_type="annual_report",
        scope1_co2e_tonnes=100.0,
        primary_activities=["activity1"]
    )
    
    response = build_merge_preview([doc])
    
    assert isinstance(response, MergePreviewResponse)
    assert response.company_name == "Test Co"
    assert response.report_year == 2023
    assert len(response.framework_versions) > 0
    
    # Check for a specific framework
    eu_taxonomy = next((fv for fv in response.framework_versions if fv.framework_id == "eu_taxonomy"), None)
    assert eu_taxonomy is not None
    assert eu_taxonomy.display_name == "EU Taxonomy"
    assert eu_taxonomy.framework_version == "2020/852"

def test_build_merge_preview_requires_same_company_and_year():
    doc1 = MergeSourceInput(company_name="A", report_year=2023)
    doc2 = MergeSourceInput(company_name="B", report_year=2023)
    
    with pytest.raises(ValueError, match="all documents must belong to the same company and report year"):
        build_merge_preview([doc1, doc2])
