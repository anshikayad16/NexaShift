import math

def explain_risk(event: str, weather: dict, aqi: int, hour: int, city: str, work_type: str) -> dict:
    factors = []
    summary_parts = []
    confidence = 70

    rainfall = weather.get("rainfall", 0)
    temp = weather.get("temp", 28)
    humidity = weather.get("humidity", 60)

    if event == "rain" or rainfall > 5:
        impact = min(100, rainfall * 3.5)
        factors.append({"name": "Rainfall Intensity", "weight": round(impact), "value": f"{rainfall} mm/hr"})
        if rainfall > 15:
            drop = min(55, round(rainfall * 1.5))
            summary_parts.append(f"Rainfall {rainfall}mm/hr → {drop}% income drop")
            confidence += 10
        elif rainfall > 5:
            drop = round(rainfall * 1.2)
            summary_parts.append(f"Light rain {rainfall}mm/hr → {drop}% order reduction")

    if event == "aqi" or aqi > 150:
        aqi_weight = min(100, round((aqi / 500) * 100))
        factors.append({"name": "Air Quality Index", "weight": aqi_weight, "value": f"AQI {aqi}"})
        if aqi > 300:
            summary_parts.append(f"AQI {aqi} (Hazardous) → outdoor work restricted")
            confidence += 8
        elif aqi > 200:
            summary_parts.append(f"AQI {aqi} (Very Unhealthy) → reduced delivery hours")

    if 11 <= hour <= 15:
        heat_weight = min(80, round((temp - 30) * 5)) if temp > 30 else 20
        factors.append({"name": "Peak Heat Hours", "weight": max(20, heat_weight), "value": f"{hour}:00 hrs, {temp}°C"})
        summary_parts.append(f"Peak heat at {hour}:00 → {max(10, round((temp-28)*2))}% productivity loss")
        confidence += 5
    elif 9 <= hour <= 11 or 18 <= hour <= 21:
        factors.append({"name": "Surge Demand Window", "weight": 85, "value": f"{hour}:00 hrs"})
        summary_parts.append(f"Surge demand at {hour}:00 → 20-40% earnings boost")
        confidence += 5

    if work_type in ("delivery", "rideshare"):
        factors.append({"name": "Outdoor Exposure Risk", "weight": 75, "value": work_type.replace("_", " ").title()})
        summary_parts.append("Outdoor gig role: weather impact amplified 1.3x")
    elif work_type == "construction":
        factors.append({"name": "Physical Risk Factor", "weight": 90, "value": "Construction"})
        summary_parts.append("Construction work: highest weather sensitivity")
    else:
        factors.append({"name": "Work Type Risk", "weight": 40, "value": work_type.replace("_", " ").title()})

    humidity_weight = round((humidity / 100) * 60)
    factors.append({"name": "Humidity Level", "weight": humidity_weight, "value": f"{humidity}%"})

    if rainfall > 15 and aqi > 200:
        factors.append({"name": "Compound Risk Alert", "weight": 95, "value": "Rain + AQI combined"})
        summary_parts.append("Combined rain+AQI → payout auto-triggered")
        confidence += 10

    if not factors:
        factors = [
            {"name": "Base Risk", "weight": 50, "value": "Standard conditions"},
            {"name": "City Factor", "weight": 40, "value": city},
        ]
        summary_parts = ["Normal conditions. Standard risk profile active."]

    confidence = min(98, confidence)
    summary = ". ".join(summary_parts) + f". AI confidence: {confidence}%." if summary_parts else "No significant risk events detected. Earnings should follow normal patterns."

    return {
        "event": event,
        "confidence": confidence,
        "factors": factors,
        "summary": summary,
        "city": city,
        "data_used": {
            "rainfall_mm_hr": rainfall,
            "temperature_c": temp,
            "humidity_pct": humidity,
            "aqi": aqi,
            "hour": hour,
        }
    }


def explain_decision(recommendation: str, reason: str, expected: float, risk_score: int, weather: dict) -> dict:
    return {
        "recommendation": recommendation,
        "reason": reason,
        "expected_earnings": expected,
        "risk_score": risk_score,
        "data_used": {
            "rainfall": weather.get("rainfall", 0),
            "temp": weather.get("temp", 28),
            "humidity": weather.get("humidity", 60),
        },
        "confidence": min(98, 65 + (100 - risk_score) // 3),
    }
