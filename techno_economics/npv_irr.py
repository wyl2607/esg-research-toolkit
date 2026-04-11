import numpy as np
from scipy.optimize import brentq


def calculate_npv(cash_flows: list[float], discount_rate: float) -> float:
    """
    计算 NPV。
    cash_flows[0] 是初始投资（负数），cash_flows[1:] 是各年现金流。
    """
    flows = np.asarray(cash_flows, dtype=float)
    periods = np.arange(flows.size, dtype=float)
    discount_factors = np.power(1.0 + discount_rate, periods)
    return round(float(np.sum(flows / discount_factors)), 2)


def calculate_irr(cash_flows: list[float]) -> float:
    """
    计算 IRR（使 NPV=0 的折现率）。
    用 brentq 在 [-0.5, 10.0] 区间求解。
    失败返回 0.0。
    """
    flows = np.asarray(cash_flows, dtype=float)
    periods = np.arange(flows.size, dtype=float)

    def npv_at_rate(rate: float) -> float:
        return float(np.sum(flows / np.power(1.0 + rate, periods)))

    lower, upper = -0.5, 10.0

    try:
        npv_lower = npv_at_rate(lower)
        npv_upper = npv_at_rate(upper)
        if npv_lower == 0:
            return round(lower, 2)
        if npv_upper == 0:
            return round(upper, 2)
        if npv_lower * npv_upper > 0:
            return 0.0
        return round(float(brentq(npv_at_rate, lower, upper)), 2)
    except (ValueError, OverflowError, ZeroDivisionError):
        return 0.0


def calculate_payback(initial_investment: float, annual_cash_flow: float) -> float:
    """
    简单回收期 = initial_investment / annual_cash_flow。
    annual_cash_flow <= 0 时返回 float('inf')。
    """
    if annual_cash_flow <= 0:
        return float("inf")
    return round(float(initial_investment / annual_cash_flow), 2)
