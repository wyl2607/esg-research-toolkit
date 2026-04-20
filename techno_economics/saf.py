"""SAF (Sustainable Aviation Fuel) levelized cost calculator.

Computes the levelized cost of SAF production (€/tonne and €/litre),
compares it against conventional Jet A-1, and calculates the breakeven
jet-fuel price at which SAF becomes cost-competitive without subsidies.

Methodology
-----------
LCOS (Levelized Cost of SAF):

    LCOS = (CAPEX_eur + Σ (OPEX_t + Feedstock_t - Policy_t) / (1+r)^t)
           / Σ Production_t / (1+r)^t

where:
    CAPEX_eur        = capex_eur_per_tonne_year × production_capacity_tonnes_year
    OPEX_t           = opex_eur_per_tonne × production_capacity_tonnes_year
    Feedstock_t      = feedstock_cost_eur_per_tonne × feedstock_to_saf_ratio
                       × production_capacity_tonnes_year
    Policy_t         = abs(policy_credit_eur_per_tonne) × production_capacity_tonnes_year
    Production_t     = production_capacity_tonnes_year  (assumed constant)
"""

import math

import numpy as np

from core.schemas import SAFCostResult, SAFInput
from techno_economics.npv_irr import calculate_irr, calculate_npv, calculate_payback

KG_PER_TONNE = 1_000.0


def calculate_saf_cost(inp: SAFInput) -> SAFCostResult:
    """Compute the levelized cost of SAF and project financials."""
    fx = inp.reference_fx_to_eur

    # --- Scale monetary inputs to EUR ---
    capex_total_eur = inp.capex_eur_per_tonne_year * inp.production_capacity_tonnes_year * fx
    annual_feedstock_cost_eur = (
        inp.feedstock_cost_eur_per_tonne
        * inp.feedstock_to_saf_ratio
        * inp.production_capacity_tonnes_year
        * fx
    )
    annual_opex_eur = inp.opex_eur_per_tonne * inp.production_capacity_tonnes_year * fx
    annual_policy_credit_eur = (
        abs(inp.policy_credit_eur_per_tonne) * inp.production_capacity_tonnes_year * fx
    )  # always positive (a saving)

    annual_production_tonnes = inp.production_capacity_tonnes_year

    # --- Discounting ---
    years = np.arange(1, inp.lifetime_years + 1, dtype=float)
    discount_factors = np.power(1.0 + inp.discount_rate, years)

    annual_total_opex = annual_feedstock_cost_eur + annual_opex_eur - annual_policy_credit_eur
    discounted_opex = float(np.sum(annual_total_opex / discount_factors))
    discounted_production = float(np.sum(annual_production_tonnes / discount_factors))

    lcos_eur_per_tonne = (capex_total_eur + discounted_opex) / discounted_production

    # Per-litre conversion: 1 tonne = 1000 kg; density (kg/L) → litres per tonne
    litres_per_tonne = KG_PER_TONNE / inp.saf_density_kg_per_litre
    lcos_eur_per_litre = lcos_eur_per_tonne / litres_per_tonne

    # Local currency
    lcos_local_per_litre = lcos_eur_per_litre / fx if fx > 0 else lcos_eur_per_litre

    # --- Cost component breakdown (per tonne, undiscounted averages) ---
    # Annualized CAPEX
    if inp.discount_rate > 0:
        crf = (inp.discount_rate * (1 + inp.discount_rate) ** inp.lifetime_years) / (
            (1 + inp.discount_rate) ** inp.lifetime_years - 1
        )
    else:
        crf = 1.0 / inp.lifetime_years
    capex_annualized = capex_total_eur * crf
    capex_per_tonne = capex_annualized / annual_production_tonnes

    feedstock_per_tonne = inp.feedstock_cost_eur_per_tonne * inp.feedstock_to_saf_ratio * fx
    opex_per_tonne = inp.opex_eur_per_tonne * fx
    policy_per_tonne = abs(inp.policy_credit_eur_per_tonne) * fx

    # --- Breakeven analysis ---
    jet_fuel_eur_per_litre = inp.jet_fuel_price_eur_per_litre * fx
    premium_pct = (
        (lcos_eur_per_litre - jet_fuel_eur_per_litre) / jet_fuel_eur_per_litre * 100.0
        if jet_fuel_eur_per_litre > 0
        else 0.0
    )
    is_competitive = lcos_eur_per_litre <= jet_fuel_eur_per_litre

    # --- NPV / IRR (from plant operator perspective) ---
    # Revenue = selling SAF at conventional jet fuel price (worst-case no premium)
    annual_revenue_eur = jet_fuel_eur_per_litre * litres_per_tonne * annual_production_tonnes
    annual_net_cf = annual_revenue_eur - annual_total_opex
    cash_flows = [-capex_total_eur] + [float(annual_net_cf)] * inp.lifetime_years

    npv_eur = calculate_npv(cash_flows, inp.discount_rate)
    irr = calculate_irr(cash_flows)
    payback = calculate_payback(capex_total_eur, float(annual_net_cf))
    payback_value: float | None = round(float(payback), 2) if math.isfinite(payback) else None

    return SAFCostResult(
        pathway=inp.pathway,
        region=inp.region,
        levelized_cost_eur_per_tonne=round(lcos_eur_per_tonne, 2),
        levelized_cost_eur_per_litre=round(lcos_eur_per_litre, 4),
        levelized_cost_local_per_litre=round(lcos_local_per_litre, 4),
        capex_component_eur_per_tonne=round(capex_per_tonne, 2),
        feedstock_component_eur_per_tonne=round(feedstock_per_tonne, 2),
        opex_component_eur_per_tonne=round(opex_per_tonne, 2),
        policy_credit_eur_per_tonne=round(policy_per_tonne, 2),
        jet_fuel_reference_eur_per_litre=round(jet_fuel_eur_per_litre, 4),
        premium_vs_conventional_pct=round(premium_pct, 1),
        breakeven_jet_fuel_price_eur_per_litre=round(lcos_eur_per_litre, 4),
        is_cost_competitive=is_competitive,
        npv_eur=round(npv_eur, 0),
        irr=round(irr, 4) if math.isfinite(irr) else 0.0,
        payback_years=payback_value,
        lifetime_years=inp.lifetime_years,
        currency=inp.currency,
        reference_fx_to_eur=inp.reference_fx_to_eur,
    )
