from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from core.schemas import (
    CompanyESGData,
    MergedMetricResult,
    MergedResult,
    MergeMetricCandidate,
    MergeMetricDecision,
    MergePreviewResponse,
    MergeSourceInput,
)

SOURCE_PRIORITY = {
    "annual_report": 400,
    "annual_sustainability_report": 350,
    "sustainability_report": 300,
    "manual_case": 250,
    "filing": 200,
    "announcement": 180,
    "event": 160,
}

METRIC_FIELDS = [
    "scope1_co2e_tonnes",
    "scope2_co2e_tonnes",
    "scope3_co2e_tonnes",
    "energy_consumption_mwh",
    "renewable_energy_pct",
    "water_usage_m3",
    "waste_recycled_pct",
    "total_revenue_eur",
    "taxonomy_aligned_revenue_pct",
    "total_capex_eur",
    "taxonomy_aligned_capex_pct",
    "total_employees",
    "female_pct",
    "primary_activities",
]


def _priority_rank(source_document_type: str | None) -> int:
    if not source_document_type:
        return 0
    return SOURCE_PRIORITY.get(source_document_type, 100)


def _timestamp_rank(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _candidate_value(document: MergeSourceInput, metric: str):
    value = getattr(document, metric)
    if value == []:
        return None
    return value


def _candidate_row(document: MergeSourceInput, metric: str) -> MergeMetricCandidate:
    source_id = document.source_id or (
        f"{document.company_name}:{document.report_year}:{document.source_document_type or 'unknown'}"
    )
    return MergeMetricCandidate(
        source_id=source_id,
        source_document_type=document.source_document_type,
        source_url=document.source_url,
        reporting_period_label=document.reporting_period_label,
        priority_rank=_priority_rank(document.source_document_type),
        value=_candidate_value(document, metric),
    )


def _sorted_candidates(
    documents: Iterable[MergeSourceInput],
    metric: str,
) -> list[MergeMetricCandidate]:
    candidates = []
    for document in documents:
        value = _candidate_value(document, metric)
        if value is None:
            continue
        row = _candidate_row(document, metric)
        candidates.append((row, _timestamp_rank(document.downloaded_at)))

    candidates.sort(
        key=lambda item: (item[0].priority_rank, item[1]),
        reverse=True,
    )
    return [row for row, _ in candidates]


def _dedupe_activity_union(candidates: list[MergeMetricCandidate]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        value = candidate.value
        if not isinstance(value, list):
            continue
        for item in value:
            if item in seen:
                continue
            seen.add(item)
            merged.append(item)
    return merged


def _reason_for(metric: str, candidates: list[MergeMetricCandidate]) -> tuple[str, bool]:
    if not candidates:
        return "missing", False

    selected = candidates[0]
    unique_values = {repr(candidate.value) for candidate in candidates}
    conflict = len(unique_values) > 1 and len(candidates) > 1

    if metric == "primary_activities" and len(candidates) > 1:
        return "activity_union", conflict
    if len(candidates) == 1:
        return "single_source", False
    if selected.source_document_type == "annual_report":
        return "annual_report_baseline", conflict
    if selected.source_document_type in {"annual_sustainability_report", "sustainability_report"}:
        return "supplement_filled_gap", conflict
    if selected.source_document_type in {"filing", "announcement", "event"}:
        return "latest_disclosure_patch", conflict
    return "highest_priority_available", conflict


def build_merge_preview(documents: list[MergeSourceInput]) -> MergePreviewResponse:
    if not documents:
        raise ValueError("documents must not be empty")

    first = documents[0]
    company_names = {document.company_name for document in documents}
    report_years = {document.report_year for document in documents}

    if len(company_names) != 1 or len(report_years) != 1:
        raise ValueError("all documents must belong to the same company and report year")

    merged_payload = {
        "company_name": first.company_name,
        "report_year": first.report_year,
        "reporting_period_label": first.reporting_period_label,
        "reporting_period_type": first.reporting_period_type,
        "source_document_type": "merged_preview",
        "evidence_summary": [],
    }
    decisions: list[MergeMetricDecision] = []
    unresolved_metrics: list[str] = []

    for metric in METRIC_FIELDS:
        candidates = _sorted_candidates(documents, metric)
        if not candidates:
            merged_payload[metric] = [] if metric == "primary_activities" else None
            continue

        reason, conflict = _reason_for(metric, candidates)
        if metric == "primary_activities":
            selected_value = _dedupe_activity_union(candidates)
        else:
            selected_value = candidates[0].value

        merged_payload[metric] = selected_value
        decisions.append(
            MergeMetricDecision(
                metric=metric,
                selected_value=selected_value,
                selected_source_id=candidates[0].source_id,
                selected_source_document_type=candidates[0].source_document_type,
                merge_reason=reason,
                candidates=candidates,
                conflict_detected=conflict,
            )
        )
        if conflict:
            unresolved_metrics.append(metric)

    merged_metrics = CompanyESGData(**merged_payload)
    return MergePreviewResponse(
        company_name=first.company_name,
        report_year=first.report_year,
        merged_metrics=merged_metrics,
        decisions=decisions,
        document_priority=[
            "annual_report",
            "annual_sustainability_report",
            "sustainability_report",
            "manual_case",
            "filing",
            "announcement",
            "event",
        ],
        unresolved_metrics=unresolved_metrics,
    )


def build_merged_result(documents: list[MergeSourceInput]) -> MergedResult:
    preview = build_merge_preview(documents)
    metrics: dict[str, MergedMetricResult] = {}
    for decision in preview.decisions:
        metrics[decision.metric] = MergedMetricResult(
            metric=decision.metric,
            chosen_value=decision.selected_value,
            candidate_values=decision.candidates,
            chosen_source=decision.selected_source_id,
            chosen_source_document_type=decision.selected_source_document_type,
            merge_reason=decision.merge_reason,
            conflict_detected=decision.conflict_detected,
        )
    return MergedResult(
        company_name=preview.company_name,
        report_year=preview.report_year,
        merged_metrics=preview.merged_metrics,
        metrics=metrics,
        source_count=len(documents),
    )
