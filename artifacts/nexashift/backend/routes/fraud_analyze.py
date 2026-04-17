"""
NexaShift Phase 3 — Fraud Analysis API
Standalone /fraud/analyze endpoint for deep multi-signal analysis.
"""
from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users
from backend.services.fraud_engine import assess_fraud_risk
from backend.routes.external import get_weather, get_aqi
from datetime import datetime

fraud_bp = Blueprint("fraud", __name__)


@fraud_bp.route("/fraud/analyze", methods=["POST"])
def fraud_analyze():
    """
    Deep fraud analysis for any claim scenario.
    Body: { user_id, claim_type, amount, description }
    Returns full signal breakdown with confidence levels.
    """
    data       = request.get_json()
    user_id    = data.get("user_id")
    claim_type = data.get("claim_type", "rain")
    amount     = float(data.get("amount", 3000))

    user = users.get(user_id, {})
    city = user.get("city", "Mumbai")

    try:
        weather = get_weather(city)
        aqi     = get_aqi(city)
    except Exception:
        weather = {"rainfall": 0, "temp": 30}
        aqi     = 100

    result = assess_fraud_risk(
        {"claim_type": claim_type, "amount": amount},
        user,
        weather=weather,
        aqi=aqi,
    )

    # Build human-readable signal table
    signals_table = []
    weight_map = result["signal_weights"]
    score_map  = result["signal_breakdown"]
    for key, label in [
        ("weather_correlation",  "Weather Correlation"),
        ("amount_anomaly",       "Amount Proportionality"),
        ("claim_frequency",      "Claim Frequency"),
        ("gps_movement_pattern", "GPS Movement Pattern"),
        ("session_timing",       "Session Timing"),
        ("device_fingerprint",   "Device Trust Score"),
    ]:
        signals_table.append({
            "signal":      label,
            "score":       score_map.get(key, 0),
            "weight_pct":  weight_map.get(key, 0),
            "contribution": round(score_map.get(key, 0) * weight_map.get(key, 0) / 100, 1),
        })

    return jsonify({
        **result,
        "signals_table":  signals_table,
        "claim_type":     claim_type,
        "amount":         amount,
        "city":           city,
        "rainfall":       weather.get("rainfall", 0),
        "aqi":            aqi,
        "analyzed_at":    datetime.utcnow().isoformat(),
    })
