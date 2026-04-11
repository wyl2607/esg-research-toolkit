"""End-to-end workflow: from ESG data to a combined report."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import requests

BASE_URL = "http://localhost:8000"
RENEWABLE_TECHNOLOGIES: dict[str, dict[str, float]] = {
    "solar_pv": {"capex": 800.0, "opex": 15.0, "cf": 0.18},
    "wind_onshore": {"capex": 1200.0, "opex": 30.0, "cf": 0.35},
    "wind_offshore": {"capex": 2500.0, "opex": 80.0, "cf": 0.45},
    "battery_storage": {"capex": 500.0, "opex": 10.0, "cf": 0.90},
}


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _post_json(url: str, payload: dict[str, Any]) -> requests.Response:
    try:
        response = requests.post(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to reach the ESG API at {BASE_URL}. "
            "Start the FastAPI server first, then retry."
        ) from exc
    return response


def _response_or_raise(response: requests.Response, action: str) -> None:
    if response.ok:
        return
    if response.status_code == 422:
        raise ValueError(
            f"{action} failed with HTTP 422. "
            f"Check the request body against the Pydantic schema. Details: {response.text}"
        )
    response.raise_for_status()


def run_full_analysis(esg_data_path: str = "examples/mock_esg_data.json") -> str:
    esg_data = _load_json(esg_data_path)
    company_name = esg_data["company_name"]
    report_year = esg_data["report_year"]
    print(f"Loaded ESG data: {company_name} ({report_year})")

    taxonomy_response = _post_json(f"{BASE_URL}/taxonomy/score", esg_data)
    _response_or_raise(taxonomy_response, "Taxonomy scoring")
    taxonomy_result = taxonomy_response.json()
    print("Taxonomy scoring complete")
    print(f"  Revenue aligned: {taxonomy_result['revenue_aligned_pct']:.1f}%")
    print(f"  DNSH pass: {taxonomy_result['dnsh_pass']}")

    report_response = _post_json(f"{BASE_URL}/taxonomy/report/text", esg_data)
    _response_or_raise(report_response, "Taxonomy report generation")
    taxonomy_report = report_response.json()["report"]

    lcoe_results: list[dict[str, Any]] = []
    for activity in esg_data.get("primary_activities", []):
        params = RENEWABLE_TECHNOLOGIES.get(activity)
        if params is None:
            continue
        lcoe_input = {
            "technology": activity,
            "capex_eur_per_kw": params["capex"],
            "opex_eur_per_kw_year": params["opex"],
            "capacity_factor": params["cf"],
            "lifetime_years": 25,
            "discount_rate": 0.07,
        }
        lcoe_response = _post_json(f"{BASE_URL}/techno/lcoe", lcoe_input)
        if not lcoe_response.ok:
            if lcoe_response.status_code == 422:
                print(f"Warning: skipped LCOE for {activity} due to invalid payload")
                print(lcoe_response.text)
                continue
            print(f"Warning: skipped LCOE for {activity}: {lcoe_response.status_code}")
            continue
        lcoe_result = lcoe_response.json()
        lcoe_results.append(lcoe_result)
        print(
            f"LCOE {activity}: {lcoe_result['lcoe_eur_per_mwh']:.1f} €/MWh, "
            f"IRR: {lcoe_result['irr'] * 100:.1f}%"
        )

    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_company = company_name.replace(" ", "_")
    report_path = output_dir / f"{safe_company}_{report_year}_full_report.txt"

    with report_path.open("w", encoding="utf-8") as handle:
        handle.write(taxonomy_report)
        handle.write("\n\n=== TECHNO-ECONOMIC ANALYSIS ===\n")
        if lcoe_results:
            for item in lcoe_results:
                handle.write(f"\n{item['technology'].upper()}\n")
                handle.write(f"  LCOE: {item['lcoe_eur_per_mwh']:.1f} €/MWh\n")
                handle.write(f"  NPV: {item['npv_eur']:,.0f} EUR\n")
                handle.write(f"  IRR: {item['irr'] * 100:.1f}%\n")
                handle.write(f"  Payback: {item['payback_years']:.1f} years\n")
        else:
            handle.write("\nNo renewable-energy activities were available for LCOE analysis.\n")

    print(f"Report saved to: {report_path}")
    return str(report_path)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    esg_data_path = args[0] if args else "examples/mock_esg_data.json"
    try:
        run_full_analysis(esg_data_path)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
