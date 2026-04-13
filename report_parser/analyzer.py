import json
import logging
import re

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

Notes on table parsing:
- Tables columns order: Indicator | Unit | 2022 | 2023 | 2024 (oldest to newest left to right).
- Always use MOST RECENT year: rightmost non-empty non-"/" column.
- "/" means no data for that year, skip and use next available year to the right.
- Numbers use comma separators: "930,440.28" -> 930440.28. Do NOT sum across years.
- "tCO 2 e" and "tCO2e" both mean tCO2e.

Unit conversions:
- Water: unit "m3" use value as-is. Unit "10 thousand m3" multiply by 10000. Unit "万吨" multiply by 10000000.
- Revenue/CapEx: unit "RMB 10 thousand" = value x 10000 / 7.8 = EUR. Unit "亿元" = value x 1e8 / 7.8 = EUR.
- Energy MWh: use as-is. Unit "万千瓦时" multiply by 10000.
- Percentages: float 0-100, do not divide by 100.

For primary_activities: snake_case strings e.g. "battery_manufacturing", "solar_pv".

Return ONLY valid JSON, no markdown, no explanation. If a field is not found, use null."""


def _extract_relevant_sections(text: str) -> str:
    """前 2000 字符（公司/年份识别）+ 后 120000 字符（数据表区域）。"""
    if not text:
        return ""
    head = text[:2000]
    tail = text[-120000:] if len(text) > 122000 else text[2000:]
    return head + "\n\n--- [ESG Data Section] ---\n\n" + tail


# ── 正则 fallback：提取基础字段 ────────────────────────────────────────────────

def _parse_number(s: str) -> float | None:
    """把 '930,440.28' 或 '93万' 类型字符串转为 float。"""
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _is_placeholder_company(name: str) -> bool:
    lowered = (name or "").strip().lower()
    return lowered in {"", "unknown", "report", "document", "file", "esg", "sustainability"}


def _extract_scope_value(text: str, labels: tuple[str, ...]) -> float | None:
    """
    更宽松地提取 Scope 数值，兼容中英日（Scope/范围/スコープ）写法，
    单位可选（部分报告把单位放在下一行）。
    """
    label_pattern = "|".join(labels)
    patterns = [
        rf"(?:{label_pattern})[^\d]{{0,220}}?([\d,]+(?:\.\d+)?)\s*(?:tCO2e|tCO₂e|万吨|吨)?",
        rf"(?:{label_pattern}).{{0,300}}?([\d,]+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        candidates: list[float] = []
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = _parse_number(match.group(1))
            if value is None:
                continue
            if "万吨" in match.group(0):
                value *= 10000
            candidates.append(value)
        if candidates:
            high_confidence = [v for v in candidates if v >= 50]
            return max(high_confidence) if high_confidence else max(candidates)
    return None


def _regex_fallback(text: str, filename: str = "") -> CompanyESGData:
    """
    当 AI 提取失败时，用正则从文本中提取最基础的字段。
    支持中英文双模式。
    """
    result: dict = {
        "company_name": "Unknown",
        "report_year": 2024,
        "scope1_co2e_tonnes": None,
        "scope2_co2e_tonnes": None,
        "scope3_co2e_tonnes": None,
        "primary_activities": [],
    }

    # 公司名：从文件名尝试提取（格式如 CATL_2024.pdf）
    if filename:
        stem = re.sub(r"\.(pdf|PDF)$", "", filename)
        parts = re.split(r"[_\-\s]+", stem)
        if parts and len(parts[0]) > 1:
            result["company_name"] = parts[0]
        # 文件名中的年份可作为兜底
        year_from_file = re.search(r"(20\d{2})", stem)
        if year_from_file:
            result["report_year"] = int(year_from_file.group(1))

    # 年份
    year_match = re.search(
        r"(20\d{2})\s*(?:年|年度|Annual|ESG|Sustainability|年报|可持续)",
        text[:3000],
        re.IGNORECASE,
    )
    if year_match:
        result["report_year"] = int(year_match.group(1))

    result["scope1_co2e_tonnes"] = _extract_scope_value(
        text, ("Scope\\s*1", "范围一", "范围\\s*1", "スコープ\\s*1")
    )
    result["scope2_co2e_tonnes"] = _extract_scope_value(
        text, ("Scope\\s*2", "范围二", "范围\\s*2", "スコープ\\s*2")
    )
    result["scope3_co2e_tonnes"] = _extract_scope_value(
        text, ("Scope\\s*3", "范围三", "范围\\s*3", "スコープ\\s*3")
    )

    return CompanyESGData(**result)


def _has_meaningful_extraction(data: CompanyESGData) -> bool:
    return any(
        [
            not _is_placeholder_company(data.company_name),
            data.scope1_co2e_tonnes is not None,
            data.scope2_co2e_tonnes is not None,
            data.scope3_co2e_tonnes is not None,
            bool(data.primary_activities),
        ]
    )


# ── 主入口 ────────────────────────────────────────────────────────────────────

class AIExtractionError(Exception):
    """AI 提取失败时抛出，携带 user-facing 原因。"""
    def __init__(self, reason: str, original: Exception | None = None):
        super().__init__(reason)
        self.reason = reason
        self.original = original


def analyze_esg_data(text: str, filename: str = "") -> CompanyESGData:
    """
    调用 AI 从文本中抽取 ESG 指标。
    - AI 成功 → 返回 CompanyESGData
    - AI 调用/解析失败 → 自动尝试 regex fallback
    - fallback 能提取关键字段时返回部分结果；否则抛出 AIExtractionError
    """
    extracted = _extract_relevant_sections(text)
    user = f"Corporate Report Text:\n\n{extracted}"

    try:
        raw = complete(_SYSTEM, user, max_tokens=2048)
    except Exception as exc:
        err_str = str(exc)
        if "401" in err_str or "authentication" in err_str.lower() or "api_key" in err_str.lower():
            reason = "AI 提取失败：API Key 无效或未配置，请检查 OPENAI_API_KEY 设置"
        elif "429" in err_str or "rate_limit" in err_str.lower():
            reason = "AI 提取失败：API 调用频率超限，请稍后重试"
        elif "timeout" in err_str.lower() or "connection" in err_str.lower():
            reason = "AI 提取失败：网络连接超时，请检查网络设置"
        else:
            reason = f"AI 提取失败：{err_str[:200]}"

        logging.warning("AI extraction failed (%s), trying regex fallback", reason)
        fallback = _regex_fallback(text, filename)
        if _has_meaningful_extraction(fallback):
            logging.info("Regex fallback extracted partial data for %s", fallback.company_name)
            return fallback
        raise AIExtractionError(reason, exc)

    try:
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        return CompanyESGData(**data)
    except Exception as exc:
        logging.warning("AI JSON parse failed, trying regex fallback: %s", exc)
        fallback = _regex_fallback(text, filename)
        if _has_meaningful_extraction(fallback):
            logging.info("Regex fallback extracted partial data for %s", fallback.company_name)
            return fallback
        raise AIExtractionError(
            "AI 返回了无效格式，且规则提取也未能识别关键字段。请确认上传文件是标准 ESG 报告。",
            exc,
        )
