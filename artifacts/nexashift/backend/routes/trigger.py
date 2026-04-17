import random
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.utils.mock_data import CITY_DATA
from backend.utils.memory_store import log_trigger

trigger_bp = Blueprint("trigger", __name__)

RAIN_THRESHOLD = 10
AQI_THRESHOLD = 250
HEAT_THRESHOLD = 42


def _build_triggers():
    from backend.routes.external import get_weather, get_aqi

    active_triggers = []
    risk_cities = []
    high_risk = False

    for city in ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune"]:
        try:
            weather = get_weather(city)
            aqi = get_aqi(city)

            rainfall = weather.get("rainfall", 0)
            temp = weather.get("temp", 28)

            if rainfall > RAIN_THRESHOLD:
                existing = next((t for t in active_triggers if t["type"] == "rain"), None)
                if existing:
                    existing["cities"].append(city)
                    existing["income_impact_percent"] = max(
                        existing["income_impact_percent"],
                        min(55, round(rainfall * 1.8))
                    )
                else:
                    impact = min(55, round(rainfall * 1.8))
                    trigger = {
                        "type": "rain",
                        "severity": "critical" if rainfall > 25 else "high",
                        "description": f"Heavy rainfall {rainfall}mm/hr detected. IMD Alert active. Delivery income expected to fall {impact}%.",
                        "income_impact_percent": impact,
                        "cities": [city],
                        "is_active": True,
                        "auto_payout": True,
                        "payout_amount": round(rainfall * 180),
                    }
                    active_triggers.append(trigger)
                    log_trigger({**trigger, "city": city})
                risk_cities.append(city)
                high_risk = True

            if aqi > AQI_THRESHOLD:
                existing = next((t for t in active_triggers if t["type"] == "aqi"), None)
                if existing:
                    existing["cities"].append(city)
                else:
                    trigger = {
                        "type": "aqi",
                        "severity": "critical" if aqi > 350 else "high" if aqi > 300 else "medium",
                        "description": f"AQI {aqi} detected in {city}. Outdoor work restricted. Health risk elevated.",
                        "income_impact_percent": min(40, round((aqi - 150) / 5)),
                        "cities": [city],
                        "is_active": True,
                        "auto_payout": aqi > 300,
                        "payout_amount": round((aqi - 200) * 8) if aqi > 200 else 0,
                    }
                    active_triggers.append(trigger)
                    log_trigger({**trigger, "city": city})
                risk_cities.append(city)
                if aqi > 300:
                    high_risk = True

            if temp > HEAT_THRESHOLD:
                existing = next((t for t in active_triggers if t["type"] == "heat"), None)
                if existing:
                    existing["cities"].append(city)
                else:
                    trigger = {
                        "type": "heat",
                        "severity": "high",
                        "description": f"Extreme heat {temp}°C in {city}. Work hours restricted 11AM–4PM.",
                        "income_impact_percent": min(35, round((temp - 38) * 4)),
                        "cities": [city],
                        "is_active": True,
                        "auto_payout": False,
                        "payout_amount": 0,
                    }
                    active_triggers.append(trigger)

        except Exception:
            continue

    if not active_triggers:
        hour = datetime.now().hour
        if 11 <= hour <= 15:
            active_triggers.append({
                "type": "heat",
                "severity": "medium",
                "description": "Peak afternoon heat. Outdoor work efficiency reduced.",
                "income_impact_percent": 15,
                "cities": ["Delhi", "Jaipur", "Ahmedabad"],
                "is_active": True,
                "auto_payout": False,
                "payout_amount": 0,
            })

    return {
        "active_triggers": active_triggers,
        "risk_level": "high" if high_risk else "medium" if active_triggers else "low",
        "affected_cities": list(set(risk_cities)),
        "auto_claims_processed": sum(1 for t in active_triggers if t.get("auto_payout")),
        "timestamp": datetime.now().isoformat(),
    }


@trigger_bp.route("/triggers", methods=["GET"])
def get_triggers():
    return jsonify(_build_triggers())
