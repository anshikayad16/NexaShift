def compute_premium(income: int, risk_score: int, weather_risk_factor: float = 1.0) -> int:
    base_premium = (income * (risk_score / 100) * 0.55 * 7) * 0.85
    adjusted = base_premium * weather_risk_factor
    return round(adjusted)


def compute_coverage(income: int, coverage_type: str = "standard") -> int:
    multipliers = {
        "basic": 2,
        "standard": 3,
        "comprehensive": 5,
    }
    return income * multipliers.get(coverage_type, 3)
