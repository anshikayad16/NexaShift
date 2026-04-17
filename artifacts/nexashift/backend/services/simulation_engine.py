from backend.utils.mock_data import SCENARIOS


def run_simulation(scenario_key: str, base_income: int,
                   weather: dict = None, aqi: int = 100) -> dict:
    scenario = SCENARIOS.get(scenario_key)
    if not scenario:
        return {"error": f"Unknown scenario: {scenario_key}"}

    impact = scenario["impact"]
    rainfall = (weather or {}).get("rainfall", 0)
    temp = (weather or {}).get("temp", 28)

    if scenario_key == "rain" and rainfall > 5:
        live_impact = min(0.70, 0.25 + rainfall * 0.018)
        impact = live_impact
    elif scenario_key == "aqi" and aqi > 150:
        live_impact = min(0.50, 0.10 + (aqi - 150) / 500)
        impact = live_impact
    elif scenario_key == "heat" and temp > 35:
        live_impact = min(0.45, 0.15 + (temp - 35) * 0.02)
        impact = live_impact

    income_drop = round(base_income * abs(impact))
    if impact < 0:
        predicted_income = base_income + income_drop
    else:
        predicted_income = max(0, base_income - income_drop)

    risk_pct = round(impact * 100)
    payout = scenario.get("payout", 0)

    live_data = {}
    if weather:
        live_data["rainfall_mm"] = rainfall
        live_data["temp_c"] = temp
        live_data["aqi"] = aqi
        live_data["impact_source"] = "live_conditions"

    explanation = (
        f"Rain {rainfall}mm/hr → {abs(risk_pct)}% income drop → auto-payout ₹{payout:,} triggered"
        if scenario_key == "rain" and rainfall > 10
        else scenario.get("description", "")
    )

    return {
        "scenario": scenario_key,
        "label": scenario["label"],
        "base_income": base_income,
        "predicted_income": predicted_income,
        "income_drop": income_drop,
        "income_drop_percent": risk_pct,
        "risk_percent": abs(risk_pct),
        "description": scenario["description"],
        "recommended_action": scenario["recommendation"],
        "expected_payout": payout,
        "net_after_payout": predicted_income + payout,
        "explanation": explanation,
        "live_conditions": live_data,
    }
