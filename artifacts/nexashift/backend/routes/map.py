from flask import Blueprint, jsonify
from backend.utils.mock_data import CITY_DATA
from datetime import datetime

map_bp = Blueprint("map", __name__)


@map_bp.route("/map-data", methods=["GET"])
def get_map_data():
    from backend.routes.external import get_weather, get_aqi
    from backend.services.risk_engine import compute_risk_score
    from backend.utils.memory_store import claims

    all_claims = [c for user_claims in claims.values() for c in user_claims]

    result = []
    for city, info in CITY_DATA.items():
        try:
            weather = get_weather(city)
            aqi = get_aqi(city)
            risk = compute_risk_score(city, "delivery", 20000, weather=weather, aqi=aqi)
        except Exception:
            weather = {"rainfall": 0, "temp": 30, "humidity": 60}
            aqi = 120
            risk = info.get("base_risk", 50)

        active = sum(1 for c in all_claims if c.get("city") == city and c.get("status") == "AUTO_APPROVED")
        rainfall = weather.get("rainfall", 0)
        temp = weather.get("temp", 28)

        aqi_level = (
            "Good" if aqi < 51 else
            "Moderate" if aqi < 101 else
            "Unhealthy for Sensitive" if aqi < 151 else
            "Unhealthy" if aqi < 201 else
            "Very Unhealthy" if aqi < 301 else
            "Hazardous"
        )

        result.append({
            "city": city,
            "lat": info["lat"],
            "lng": info["lng"],
            "risk_score": risk,
            "demand_score": info["demand"],
            "avg_payout": info["avg_payout"],
            "active_claims": active,
            "weather": weather.get("description", info["weather"]),
            "rainfall": rainfall,
            "temp": temp,
            "aqi": aqi,
            "aqi_level": aqi_level,
            "timestamp": datetime.now().isoformat(),
        })

    return jsonify(result)
