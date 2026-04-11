import json
import logging

from core.ai_client import complete
from core.schemas import CompanyESGData

_SYSTEM = """You are an ESG data analyst. Extract ESG metrics from the provided corporate report text and return a JSON object with these fields:

- company_name: string
- report_year: integer (e.g. 2023)
- scope1_co2e_tonnes: float or null
- scope2_co2e_tonnes: float or null
- scope3_co2e_tonnes: float or null
- energy_consumption_mwh: float or null
- renewable_energy_pct: float (0-100) or null
- water_usage_m3: float or null
- waste_recycled_pct: float (0-100) or null
- total_revenue_eur: float or null
- taxonomy_aligned_revenue_pct: float (0-100) or null
- total_capex_eur: float or null
- taxonomy_aligned_capex_pct: float (0-100) or null
- total_employees: integer or null
- female_pct: float (0-100) or null
- primary_activities: list of strings (e.g. ["solar_pv", "wind_onshore"])

Return ONLY valid JSON, no markdown, no explanation. If a field is not found, use null."""


def analyze_esg_data(text: str) -> CompanyESGData:
    """
    调用 OpenAI 从文本中抽取 ESG 指标。
    text 截取前 8000 字符（避免超 token 限制）。
    JSON 解析失败时返回默认 CompanyESGData（company_name="Unknown", report_year=2024）。
    """
    user = f"Corporate Report Text:\n\n{text[:8000]}"
    try:
        raw = complete(_SYSTEM, user, max_tokens=1024)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        return CompanyESGData(**data)
    except Exception as exc:
        logging.warning("analyze_esg_data failed: %s", exc)
        return CompanyESGData(company_name="Unknown", report_year=2024)
