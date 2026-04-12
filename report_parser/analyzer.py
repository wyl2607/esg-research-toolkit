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

Notes:
- Data is often in table format with columns for multiple years; use the most recent year (rightmost column).
- Numbers may appear as "930,440.28" (with commas) — parse as float.
- Revenue may be in RMB or local currency. If in RMB "10 thousand" units, multiply by 10000 then convert to EUR (1 EUR ≈ 7.8 RMB as of 2024).
- Scope 1/2/3 emissions are in tCO2e. Energy in MWh. Water in m3.
- For primary_activities use snake_case strings describing the company's main business.

Return ONLY valid JSON, no markdown, no explanation. If a field is not found, use null."""


def _extract_relevant_sections(text: str) -> str:
    """
    ESG 报告数据通常集中在报告末尾的数据表章节。
    策略：前 2000 字符（公司/年份识别）+ 后 100000 字符（数据表）。
    """
    if not text:
        return ""
    head = text[:2000]
    tail = text[-120000:] if len(text) > 122000 else text[2000:]
    return head + "\n\n--- [ESG Data Section] ---\n\n" + tail


def analyze_esg_data(text: str) -> CompanyESGData:
    """
    调用 OpenAI 从文本中抽取 ESG 指标。
    text 按关键词提取相关片段（包含文首 + 指标窗口），总长度限制为 30000 字符。
    JSON 解析失败时返回默认 CompanyESGData（company_name="Unknown", report_year=2024）。
    """
    extracted = _extract_relevant_sections(text)
    user = f"Corporate Report Text:\n\n{extracted}"
    try:
        raw = complete(_SYSTEM, user, max_tokens=2048)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        return CompanyESGData(**data)
    except Exception as exc:
        logging.warning("analyze_esg_data failed: %s", exc)
        return CompanyESGData(company_name="Unknown", report_year=2024)
