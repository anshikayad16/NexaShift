"""
NexaShift Phase 3 — Hyper-Local Micro-zone Intelligence
Returns zone-level risk, demand, and recommendations inside a city.
"""
from flask import Blueprint, request, jsonify
from backend.utils.mock_data import MICRO_ZONES, CITY_DATA
from backend.services.risk_engine import compute_risk_score
from backend.routes.external import get_weather, get_aqi
import random
from datetime import datetime

microzones_bp = Blueprint("microzones", __name__)


def _zone_risk(zone, city_risk, rainfall, aqi):
    """
    Zone risk = city base risk ± zone offset ± live weather adjustment.
    """
    offset    = zone.get("risk_offset", 0)
    rain_adj  = min(20, rainfall * 1.5)
    aqi_adj   = max(0, (aqi - 150) / 20)
    raw       = city_risk + offset + rain_adj + aqi_adj
    return min(95, max(10, round(raw)))


def _zone_demand(zone, hour):
    """Demand fluctuates with time of day and zone type."""
    base     = zone.get("demand", 75)
    zone_type = zone.get("type", "residential")
    type_mult = {
        "commercial":  {7: 0.7, 8: 1.1, 9: 1.2, 10: 1.1, 11: 1.0, 12: 1.2,
                        13: 1.1, 14: 0.9, 15: 0.8, 16: 0.9, 17: 1.2, 18: 1.4, 19: 1.3, 20: 1.2},
        "corporate":   {7: 0.6, 8: 1.3, 9: 1.4, 10: 1.2, 17: 1.5, 18: 1.6, 19: 1.2},
        "residential": {7: 1.2, 8: 1.3, 12: 1.1, 13: 1.0, 18: 1.3, 19: 1.4, 20: 1.3},
        "transit_hub": {7: 1.4, 8: 1.5, 9: 1.3, 17: 1.5, 18: 1.6, 19: 1.4},
        "nightlife":   {18: 1.1, 19: 1.4, 20: 1.7, 21: 1.8, 22: 1.6},
        "market":      {10: 1.2, 11: 1.3, 12: 1.2, 13: 1.1, 16: 1.3, 17: 1.4, 18: 1.5},
        "suburb":      {7: 1.1, 8: 1.2, 18: 1.2, 19: 1.3},
        "industrial":  {7: 1.3, 8: 1.4, 9: 1.2, 16: 1.3, 17: 1.2},
    }.get(zone_type, {})
    mult = type_mult.get(hour, 0.85)
    return min(100, max(10, round(base * mult)))


@microzones_bp.route("/microzones/<city>", methods=["GET"])
def get_microzones(city):
    zones = MICRO_ZONES.get(city)
    if not zones:
        return jsonify({"error": f"No micro-zone data for {city}"}), 404

    city_info = CITY_DATA.get(city, {})
    city_base_risk = city_info.get("base_risk", 50)

    try:
        weather  = get_weather(city)
        aqi      = get_aqi(city)
        rainfall = weather.get("rainfall", 0)
    except Exception:
        weather  = {"rainfall": 0, "temp": 30}
        aqi      = 100
        rainfall = 0

    hour = datetime.now().hour

    result = []
    for z in zones:
        risk   = _zone_risk(z, city_base_risk, rainfall, aqi)
        demand = _zone_demand(z, hour)

        rec = (
            f"High demand, low risk — prime earning zone now ({z['peak_hours']})"
            if risk < 45 and demand > 80
            else f"Moderate conditions — caution advised. Best hours: {z['peak_hours']}"
            if risk < 65
            else f"Risky zone right now — consider switching areas or filing a preemptive claim"
        )

        result.append({
            "zone":       z["zone"],
            "city":       city,
            "lat":        z["lat"],
            "lng":        z["lng"],
            "risk":       risk,
            "demand":     demand,
            "type":       z.get("type", "general"),
            "peak_hours": z.get("peak_hours", "—"),
            "rainfall":   rainfall,
            "aqi":        aqi,
            "recommendation": rec,
            "action":     "WORK" if risk < 45 else "OPTIONAL" if risk < 65 else "AVOID",
        })

    result.sort(key=lambda x: x["demand"], reverse=True)
    return jsonify({
        "city":       city,
        "zones":      result,
        "timestamp":  datetime.utcnow().isoformat(),
        "city_risk":  city_base_risk,
        "rainfall":   rainfall,
        "aqi":        aqi,
    })


@microzones_bp.route("/microzones/all", methods=["GET"])
def all_microzones():
    """Return all zones across all cities for the map overlay."""
    result  = []
    hour    = datetime.now().hour
    for city, zones in MICRO_ZONES.items():
        city_info   = CITY_DATA.get(city, {})
        city_risk   = city_info.get("base_risk", 50)
        try:
            weather  = get_weather(city)
            rainfall = weather.get("rainfall", 0)
            aqi      = get_aqi(city)
        except Exception:
            rainfall = 0
            aqi      = 100
        for z in zones:
            risk   = _zone_risk(z, city_risk, rainfall, aqi)
            demand = _zone_demand(z, hour)
            result.append({
                "zone":   z["zone"],
                "city":   city,
                "lat":    z["lat"],
                "lng":    z["lng"],
                "risk":   risk,
                "demand": demand,
                "type":   z.get("type", "general"),
                "action": "WORK" if risk < 45 else "OPTIONAL" if risk < 65 else "AVOID",
            })
    return jsonify(result)
