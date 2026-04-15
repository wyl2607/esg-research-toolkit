import json
import logging
import os
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
    """前 2000 字符（公司/年份识别）+ ESG 关键词覆盖区域（最多 110000 字符）。

    策略：在全文中定位所有 ESG 关键词，每处建 ±15K 窗口并合并，
    按关键词密度降序选取，总量不超过 110K。避免长报告（如钢铁/化工年报）
    中间的 ESG 表格被截断丢失。
    """
    if not text:
        return ""

    head = text[:2000]

    # 如果文本较短，直接返回全文
    if len(text) <= 122000:
        return head + "\n\n--- [ESG Data Section] ---\n\n" + text[2000:]

    # 定位全文中所有 ESG 关键词
    esg_keywords = [
        r"scope\s*1", r"scope\s*2", r"scope\s*3",
        r"tco2e?", r"co2e", r"co2eq", r"co₂e",
        r"greenhouse\s*gas", r"ghg\s+emission",
        r"renewable\s+energy", r"energy\s+consumption",
        r"sustainability\s+data", r"esg\s+data", r"key\s+performance",
        r"million\s+tons?\s+co2", r"kt\s+co2", r"tonnes?\s+co2",
    ]
    positions = []
    for pat in esg_keywords:
        for m in re.finditer(pat, text, re.IGNORECASE):
            positions.append(m.start())

    if not positions:
        return head + "\n\n--- [ESG Data Section] ---\n\n" + text[-120000:]

    # 每个关键词位置前后 15K 建窗口，合并重叠区间
    WIN = 15000
    intervals = sorted((max(0, p - WIN), min(len(text), p + WIN)) for p in positions)
    merged: list[list[int]] = []
    for s, e in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    # 按关键词密度降序排列（优先高密度区域）
    def _density(interval: list[int]) -> int:
        chunk = text[interval[0]:interval[1]]
        return sum(len(re.findall(pat, chunk, re.IGNORECASE)) for pat in esg_keywords)

    merged.sort(key=_density, reverse=True)

    # 选取密度最高的区域，总量不超过 110K
    BUDGET = 110000
    selected: list[tuple[int, int]] = []
    used = 0
    for s, e in merged:
        size = e - s
        if used + size <= BUDGET:
            selected.append((s, e))
            used += size
        else:
            remaining = BUDGET - used
            if remaining > 2000:
                selected.append((s, s + remaining))
            break

    # 按原文顺序拼接
    selected.sort()
    esg_parts = [text[s:e] for s, e in selected]

    return (
        head
        + "\n\n--- [ESG Data Section] ---\n\n"
        + "\n\n--- [next section] ---\n\n".join(esg_parts)
    )


# ── 正则 fallback：提取基础字段 ────────────────────────────────────────────────

def _parse_number(s: str) -> float | None:
    """把 '930,440.28' 这类字符串转为 float。"""
    s = s.strip().replace(" ", "").replace("，", ",")
    if not s:
        return None

    # Handle mixed separators by treating the last separator as decimal.
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # German style: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:
            # English style: 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        # Only comma present: decimal if short suffix, else thousands.
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s:
        # Only dot present: detect German thousands style like 11.200 or 9.800.
        parts = s.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            s = "".join(parts)

    try:
        return float(s)
    except ValueError:
        return None


def _parse_scaled_value(number_str: str, context: str) -> float | None:
    val = _parse_number(number_str)
    if val is None:
        return None

    lowered = context.lower()
    if "亿" in context:
        return val * 1e8
    if "万" in context:
        return val * 1e4
    if "10 thousand" in lowered:
        return val * 1e4
    if "million" in lowered:
        return val * 1e6
    if "billion" in lowered:
        return val * 1e9
    return val


def _extract_metric(text: str, patterns: list[str]) -> float | None:
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if not match:
            continue
        value = _parse_scaled_value(match.group(1), match.group(0))
        if value is not None:
            return value
    return None


def _extract_percentage(text: str, patterns: list[str]) -> float | None:
    value = _extract_metric(text, patterns)
    if value is None:
        return None
    if 0 <= value <= 100:
        return value
    if 0 <= value <= 1:
        return value * 100
    return None


def _extract_primary_activities(text: str) -> list[str]:
    mapping = {
        "solar_pv": [r"solar(?:\s+pv)?", r"光伏", r"太阳能"],
        "wind_onshore": [r"onshore\s+wind", r"陆上风电"],
        "wind_offshore": [r"offshore\s+wind", r"海上风电"],
        "battery_storage": [r"battery\s+storage", r"储能", r"电池储能"],
        "battery_manufacturing": [r"battery\s+manufactur", r"电池制造"],
        "hydrogen": [r"hydrogen", r"氢能"],
    }
    lowered = text.lower()
    activities: list[str] = []
    for activity, pats in mapping.items():
        if any(re.search(pat, lowered, re.IGNORECASE) for pat in pats):
            activities.append(activity)
    return activities


def _is_fallback_usable(data: CompanyESGData) -> bool:
    return any(
        value is not None
        for value in [
            data.scope1_co2e_tonnes,
            data.scope2_co2e_tonnes,
            data.scope3_co2e_tonnes,
            data.energy_consumption_mwh,
            data.renewable_energy_pct,
            data.water_usage_m3,
            data.waste_recycled_pct,
            data.taxonomy_aligned_revenue_pct,
            data.taxonomy_aligned_capex_pct,
            data.total_employees,
            data.female_pct,
        ]
    )


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
        "energy_consumption_mwh": None,
        "renewable_energy_pct": None,
        "water_usage_m3": None,
        "waste_recycled_pct": None,
        "taxonomy_aligned_revenue_pct": None,
        "taxonomy_aligned_capex_pct": None,
        "total_employees": None,
        "female_pct": None,
        "primary_activities": [],
    }

    # 公司名：从文件名尝试提取（格式如 CATL_2024.pdf）
    if filename:
        stem = re.sub(r"\.(pdf|PDF)$", "", filename)
        parts = re.split(r"[_\-\s]+", stem)
        if parts and len(parts[0]) > 1:
            result["company_name"] = parts[0]

    # 年份
    year_match = re.search(
        r"(20\d{2})\s*(?:年|年度|Annual|ESG|Sustainability|年报|可持续)",
        text[:3000],
        re.IGNORECASE,
    )
    if year_match:
        result["report_year"] = int(year_match.group(1))

    # CO2 unit alternatives (tCO2e, kt CO2e, Mt CO2e, Mio. t CO2e, million tons CO2, 万吨, 吨)
    _CO2_UNIT = r"(?:tCO2e?q?|tCO₂e?|t\s*CO2e?q?|kt\s*CO2e?q?|Mt\s*CO2e?q?|Tt\s*CO2e?q?|Mio\.?\s*t\s*CO2e?q?|million\s+t(?:ons?|onnes?)\s*CO2e?q?|万吨|吨)"

    def _scope_extract(label_pat: str, text: str) -> float | None:
        # Allow up to 120 chars (including newlines) between label and value
        m = re.search(
            rf"(?:{label_pat})[\s\S]{{0,120}}?([\d,.]+)\s*{_CO2_UNIT}",
            text, re.IGNORECASE,
        )
        if not m:
            return None
        raw = m.group(1).strip()
        val = _parse_number(raw)
        if val is None:
            return None
        full = m.group(0).lower()
        if "万吨" in full:
            val *= 10000
        elif re.search(r"\bkt\b", full):
            val *= 1000
        elif re.search(r"\bmt\b|\bmio\b|\bmillion\b", full):
            val *= 1e6
        elif re.search(r"\btt\b", full):
            val *= 1e12
        return val

    result["scope1_co2e_tonnes"] = _scope_extract(r"Scope\s*1|范围一|范围\s*1", text)
    result["scope2_co2e_tonnes"] = _scope_extract(r"Scope\s*2|范围二|范围\s*2", text)
    result["scope3_co2e_tonnes"] = _scope_extract(r"Scope\s*3|范围三|范围\s*3", text)

    result["energy_consumption_mwh"] = _extract_metric(
        text,
        [
            r"(?:energy consumption|energy used|能源消费总量|综合能耗|energieverbrauch|gesamtenergieverbrauch)[^\d]{0,40}([\d,.]+)\s*(?:mwh|兆瓦时|万千瓦时|kwh)",
        ],
    )
    if result["energy_consumption_mwh"] and re.search(r"万千瓦时", text, re.IGNORECASE):
        result["energy_consumption_mwh"] = result["energy_consumption_mwh"] * 10000 / 1000
    if result["energy_consumption_mwh"] and re.search(r"\bkwh\b", text, re.IGNORECASE):
        result["energy_consumption_mwh"] = result["energy_consumption_mwh"] / 1000

    result["renewable_energy_pct"] = _extract_percentage(
        text,
        [
            r"(?:renewable energy(?: ratio| share| percentage)?|可再生能源(?:占比|比例)?|anteil erneuerbarer energien|erneuerbare(?:r)?\s+energie(?:n)?(?:anteil|quote)?)[^\d]{0,40}([\d,.]+)\s*%",
        ],
    )

    result["water_usage_m3"] = _extract_metric(
        text,
        [
            r"(?:water (?:consumption|usage)|用水(?:总量|量)?|wasserverbrauch|wasserentnahme)[^\d]{0,40}([\d,.]+)\s*(?:m3|m³|立方米|万立方米|万m3)",
        ],
    )
    if result["water_usage_m3"] and re.search(r"(万立方米|万m3)", text, re.IGNORECASE):
        result["water_usage_m3"] *= 10000

    result["waste_recycled_pct"] = _extract_percentage(
        text,
        [
            r"(?:waste recycled(?: rate| percentage)?|waste recycling(?: rate)?|废弃物(?:回收率|资源化利用率)|循环利用率|recyclingquote|abfall(?:recycling|verwertungs)quote)[^\d]{0,40}([\d,.]+)\s*%",
        ],
    )

    result["taxonomy_aligned_revenue_pct"] = _extract_percentage(
        text,
        [
            r"(?:taxonomy[-\s]?aligned revenue|taxonomy alignment(?: of)? revenue|分类法对齐(?:收入|营收)占比|taxonomiekonformer(?:r)?\s+umsatz|umsatz(?:anteil)?\s+taxonomiekonform)[^\d]{0,40}([\d,.]+)\s*%",
        ],
    )
    result["taxonomy_aligned_capex_pct"] = _extract_percentage(
        text,
        [
            r"(?:taxonomy[-\s]?aligned capex|taxonomy alignment(?: of)? capex|分类法对齐(?:资本开支|capex)占比|taxonomiekonformer(?:s)?\s+capex|capex(?:anteil)?\s+taxonomiekonform)[^\d]{0,40}([\d,.]+)\s*%",
        ],
    )

    employees = _extract_metric(
        text,
        [
            r"(?:total employees|number of employees|员工总数|职工总数|mitarbeiter(?:zahl)?|anzahl der mitarbeiter)[^\d]{0,40}([\d,.]+)\s*(?:people|人)?",
        ],
    )
    result["total_employees"] = int(employees) if employees is not None else None

    result["female_pct"] = _extract_percentage(
        text,
        [
            r"(?:female(?: employee)?(?: ratio| percentage)?|women employees(?: ratio| percentage)?|女性员工(?:占比|比例)?|女员工比例|frauenanteil|anteil weiblicher mitarbeiter(?:innen)?)[^\d]{0,40}([\d,.]+)\s*%",
        ],
    )

    result["primary_activities"] = _extract_primary_activities(text)

    return CompanyESGData(**result)


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
    - AI 失败（API 错误）→ 抛出 AIExtractionError
    - JSON 解析失败 → 先尝试正则 fallback；fallback 也无法提取则抛出 AIExtractionError
    """
    fallback = _regex_fallback(text, filename)
    regex_only_mode = os.getenv("PARSER_REGEX_ONLY", "0").lower() in {"1", "true", "yes"}
    if regex_only_mode and _is_fallback_usable(fallback):
        logging.info("PARSER_REGEX_ONLY enabled, returning regex extraction for %s", fallback.company_name)
        return fallback

    extracted = _extract_relevant_sections(text)
    user = f"Corporate Report Text:\n\n{extracted}"

    try:
        raw = complete(_SYSTEM, user, max_tokens=2048)
    except Exception as exc:
        if _is_fallback_usable(fallback):
            logging.warning("AI call failed, returning regex fallback: %s", exc)
            return fallback
        err_str = str(exc)
        if "401" in err_str or "authentication" in err_str.lower() or "api_key" in err_str.lower():
            raise AIExtractionError("AI 提取失败：API Key 无效或未配置，请检查 OPENAI_API_KEY 设置", exc)
        if "429" in err_str or "rate_limit" in err_str.lower():
            raise AIExtractionError("AI 提取失败：API 调用频率超限，请稍后重试", exc)
        if "timeout" in err_str.lower() or "connection" in err_str.lower():
            raise AIExtractionError("AI 提取失败：网络连接超时，请检查网络设置", exc)
        raise AIExtractionError(f"AI 提取失败：{err_str[:200]}", exc)

    try:
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        return CompanyESGData(**data)
    except Exception as exc:
        logging.warning("AI JSON parse failed, trying regex fallback: %s", exc)
        if _is_fallback_usable(fallback):
            logging.info("Regex fallback extracted partial data for %s", fallback.company_name)
            return fallback
        raise AIExtractionError(
            "AI 返回了无效格式，且规则提取也未能识别关键字段。请确认上传文件是标准 ESG 报告。",
            exc,
        )
