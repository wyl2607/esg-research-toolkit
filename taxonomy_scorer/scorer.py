from core.schemas import CompanyESGData, TaxonomyScoreResult
from taxonomy_scorer.framework import OBJECTIVES, get_activity


def _check_dnsh(data: CompanyESGData, activity_id: str) -> bool:
    """
    Simplified DNSH check:
    - water: water_usage_m3 must be disclosed
    - circular_economy: waste_recycled_pct must be disclosed
    - other objectives: pass by default until stricter data is available
    """
    activity = get_activity(activity_id)
    if not activity:
        return False

    checks = {
        "climate_adaptation": True,
        "water": data.water_usage_m3 is not None,
        "circular_economy": data.waste_recycled_pct is not None,
        "pollution": True,
        "biodiversity": True,
    }
    return all(checks.get(obj, True) for obj in activity.dnsh_objectives)


def _score_activity_alignment(data: CompanyESGData, activity_id: str) -> float:
    """
    Calculate single-activity alignment score in the range 0.0-1.0.
    """
    if activity_id not in data.primary_activities:
        return 0.0

    activity = get_activity(activity_id)
    if not activity:
        return 0.0

    score = 0.5

    if activity.ghg_threshold_gco2e_per_kwh and data.energy_consumption_mwh:
        total_ghg = (data.scope1_co2e_tonnes or 0) + (data.scope2_co2e_tonnes or 0)
        ghg_intensity = (
            (total_ghg * 1_000_000) / (data.energy_consumption_mwh * 1000)
            if data.energy_consumption_mwh > 0
            else 999
        )
        if ghg_intensity < activity.ghg_threshold_gco2e_per_kwh:
            score += 0.3

    if data.renewable_energy_pct and data.renewable_energy_pct >= 50:
        score += 0.2

    return min(score, 1.0)


def score_company(data: CompanyESGData) -> TaxonomyScoreResult:
    """
    Score a company against simplified EU Taxonomy alignment logic.
    """
    objective_scores: dict[str, float] = {obj: 0.0 for obj in OBJECTIVES}

    climate_mitigation_activities = {
        "solar_pv",
        "wind_onshore",
        "wind_offshore",
        "battery_storage",
        "energy_storage",
        "battery_manufacturing",
        "battery_materials",
    }
    circular_economy_activities = {"battery_recycling"}

    active_climate = [a for a in data.primary_activities if a in climate_mitigation_activities]
    if active_climate:
        scores = [_score_activity_alignment(data, a) for a in active_climate]
        objective_scores["climate_mitigation"] = sum(scores) / len(scores)

    active_circular = [a for a in data.primary_activities if a in circular_economy_activities]
    if active_circular:
        # Battery recycling directly contributes to circular economy objective
        base = 0.6
        if data.waste_recycled_pct is not None:
            base = max(base, min(data.waste_recycled_pct / 100, 1.0))
        objective_scores["circular_economy"] = max(objective_scores["circular_economy"], base)

    if data.scope3_co2e_tonnes is not None:
        objective_scores["climate_adaptation"] = 0.5

    if data.water_usage_m3 is not None:
        objective_scores["water"] = 0.6

    if data.waste_recycled_pct is not None:
        waste_score = min(data.waste_recycled_pct / 100, 1.0)
        objective_scores["circular_economy"] = max(objective_scores["circular_economy"], waste_score)

    objective_scores["pollution"] = 0.0
    objective_scores["biodiversity"] = 0.0

    dnsh_pass = (
        all(_check_dnsh(data, activity_id) for activity_id in data.primary_activities)
        if data.primary_activities
        else False
    )

    revenue_aligned = data.taxonomy_aligned_revenue_pct or (
        objective_scores["climate_mitigation"] * 100 if active_climate else 0.0
    )
    capex_aligned = data.taxonomy_aligned_capex_pct or revenue_aligned

    gaps = _identify_gaps(data, objective_scores)
    recommendations = _generate_recommendations(gaps, objective_scores)

    return TaxonomyScoreResult(
        company_name=data.company_name,
        report_year=data.report_year,
        revenue_aligned_pct=round(revenue_aligned, 1),
        capex_aligned_pct=round(capex_aligned, 1),
        opex_aligned_pct=round(revenue_aligned * 0.8, 1),
        objective_scores={k: round(v, 2) for k, v in objective_scores.items()},
        dnsh_pass=dnsh_pass,
        gaps=gaps,
        recommendations=recommendations,
    )


def _identify_gaps(data: CompanyESGData, objective_scores: dict[str, float]) -> list[str]:
    gaps = []
    if data.scope1_co2e_tonnes is None:
        gaps.append("Missing Scope 1 GHG emissions data")
    if data.scope2_co2e_tonnes is None:
        gaps.append("Missing Scope 2 GHG emissions data")
    if data.scope3_co2e_tonnes is None:
        gaps.append("Missing Scope 3 GHG emissions data")
    if data.water_usage_m3 is None:
        gaps.append("Missing water usage data (required for DNSH water objective)")
    if data.waste_recycled_pct is None:
        gaps.append("Missing waste recycling rate (required for circular economy objective)")
    if not data.primary_activities:
        gaps.append("No taxonomy-eligible activities identified")
    if objective_scores.get("climate_mitigation", 0) < 0.5:
        gaps.append(
            "Climate mitigation alignment below 50% - consider renewable energy investments"
        )
    return gaps


def _generate_recommendations(
    gaps: list[str], objective_scores: dict[str, float]
) -> list[str]:
    recs = []
    if any("Scope" in gap for gap in gaps):
        recs.append("Implement GHG accounting across Scope 1, 2, and 3 per GHG Protocol")
    if any("water" in gap.lower() for gap in gaps):
        recs.append("Disclose water consumption and withdrawal data per ESRS E3")
    if any("waste" in gap.lower() for gap in gaps):
        recs.append(
            "Report waste recycling rates per ESRS E5 circular economy requirements"
        )
    if any("activities" in gap for gap in gaps):
        recs.append(
            "Map business activities to EU Taxonomy NACE codes to identify eligible activities"
        )
    if objective_scores.get("climate_mitigation", 0) < 0.3:
        recs.append(
            "Develop a renewable energy transition plan to improve climate mitigation alignment"
        )
    return recs
