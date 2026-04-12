from dataclasses import dataclass, field


@dataclass
class TechnicalScreeningCriteria:
    activity_id: str
    name: str
    sector: str
    ghg_threshold_gco2e_per_kwh: float | None = None
    renewable_energy_min_pct: float | None = None
    dnsh_objectives: list[str] = field(default_factory=list)


ACTIVITIES: dict[str, TechnicalScreeningCriteria] = {
    "solar_pv": TechnicalScreeningCriteria(
        activity_id="solar_pv",
        name="Electricity generation using solar photovoltaic technology",
        sector="Energy",
        ghg_threshold_gco2e_per_kwh=100.0,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
    "wind_onshore": TechnicalScreeningCriteria(
        activity_id="wind_onshore",
        name="Electricity generation from wind power (onshore)",
        sector="Energy",
        ghg_threshold_gco2e_per_kwh=100.0,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
    "wind_offshore": TechnicalScreeningCriteria(
        activity_id="wind_offshore",
        name="Electricity generation from wind power (offshore)",
        sector="Energy",
        ghg_threshold_gco2e_per_kwh=100.0,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
    "battery_storage": TechnicalScreeningCriteria(
        activity_id="battery_storage",
        name="Storage of electricity",
        sector="Energy",
        ghg_threshold_gco2e_per_kwh=100.0,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
    "building_renovation": TechnicalScreeningCriteria(
        activity_id="building_renovation",
        name="Renovation of existing buildings",
        sector="Buildings",
        renewable_energy_min_pct=None,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
    "district_heating": TechnicalScreeningCriteria(
        activity_id="district_heating",
        name="District heating/cooling distribution",
        sector="Energy",
        ghg_threshold_gco2e_per_kwh=100.0,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
    # EU Taxonomy Annex I, Activity 3.1 — Manufacture of low carbon technologies for transport
    "battery_manufacturing": TechnicalScreeningCriteria(
        activity_id="battery_manufacturing",
        name="Manufacture of batteries for low-carbon transport (EU Taxonomy 3.1)",
        sector="Manufacturing",
        ghg_threshold_gco2e_per_kwh=250.0,  # gCO2e per kWh energy consumed in manufacturing
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
    # EU Taxonomy Annex I, Activity 4.8 — Manufacture of renewable energy equipment
    "battery_materials": TechnicalScreeningCriteria(
        activity_id="battery_materials",
        name="Manufacture of battery materials for renewable energy storage (EU Taxonomy 4.8)",
        sector="Manufacturing",
        ghg_threshold_gco2e_per_kwh=250.0,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
    # EU Taxonomy Annex I, Activity 5.11 — Recycling of batteries
    "battery_recycling": TechnicalScreeningCriteria(
        activity_id="battery_recycling",
        name="Recycling of batteries and e-waste (EU Taxonomy 5.11)",
        sector="Circular Economy",
        ghg_threshold_gco2e_per_kwh=None,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "pollution",
            "biodiversity",
        ],
    ),
    # Alias: energy_storage → maps to battery_storage logic
    "energy_storage": TechnicalScreeningCriteria(
        activity_id="energy_storage",
        name="Storage of electricity (battery / grid-scale)",
        sector="Energy",
        ghg_threshold_gco2e_per_kwh=100.0,
        dnsh_objectives=[
            "climate_adaptation",
            "water",
            "circular_economy",
            "pollution",
            "biodiversity",
        ],
    ),
}

OBJECTIVES = [
    "climate_mitigation",
    "climate_adaptation",
    "water",
    "circular_economy",
    "pollution",
    "biodiversity",
]


def get_activity(activity_id: str) -> TechnicalScreeningCriteria | None:
    return ACTIVITIES.get(activity_id)


def list_activities() -> list[TechnicalScreeningCriteria]:
    return list(ACTIVITIES.values())
