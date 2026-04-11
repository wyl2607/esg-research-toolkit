from dataclasses import dataclass

from core.schemas import CompanyESGData, TaxonomyScoreResult
from taxonomy_scorer.framework import OBJECTIVES


@dataclass
class GapItem:
    objective: str
    severity: str
    description: str
    action: str


def analyze_gaps(data: CompanyESGData, result: TaxonomyScoreResult) -> list[GapItem]:
    """Generate a detailed list of compliance gaps."""
    gaps: list[GapItem] = []

    if result.objective_scores.get("climate_mitigation", 0) < 0.3:
        gaps.append(
            GapItem(
                objective="climate_mitigation",
                severity="critical",
                description=(
                    "Climate mitigation score "
                    f"{result.objective_scores.get('climate_mitigation', 0):.0%} "
                    "- below minimum threshold"
                ),
                action=(
                    "Identify and disclose taxonomy-eligible renewable energy "
                    "activities (solar PV, wind, storage)"
                ),
            )
        )

    missing_scopes = [
        scope
        for scope in ["scope1", "scope2", "scope3"]
        if getattr(data, f"{scope}_co2e_tonnes") is None
    ]
    if missing_scopes:
        gaps.append(
            GapItem(
                objective="climate_mitigation",
                severity="critical" if "scope1" in missing_scopes else "major",
                description=(
                    "Missing GHG data: "
                    + ", ".join(missing_scopes).replace("scope", "Scope ")
                ),
                action="Implement GHG inventory per GHG Protocol Corporate Standard",
            )
        )

    if not result.dnsh_pass:
        gaps.append(
            GapItem(
                objective="water",
                severity="major",
                description=(
                    "DNSH check failed - insufficient environmental safeguard disclosures"
                ),
                action="Disclose water usage (ESRS E3) and waste management data (ESRS E5)",
            )
        )

    for obj in OBJECTIVES:
        score = result.objective_scores.get(obj, 0)
        if score == 0.0 and obj not in ("pollution", "biodiversity"):
            gaps.append(
                GapItem(
                    objective=obj,
                    severity="minor",
                    description=f"No data available for {obj.replace('_', ' ')} objective",
                    action=(
                        "Collect and disclose relevant indicators for "
                        f"{obj.replace('_', ' ')}"
                    ),
                )
            )

    return gaps
