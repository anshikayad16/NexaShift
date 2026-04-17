"""
NexaShift Phase 3 — ML Prediction API Endpoints
Exposes the ML engine models as REST APIs.
"""
from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users, claims
from backend.services.ml_engine import predict_risk, predict_loss, compute_premium, predict_claims_tomorrow
from backend.utils.mock_data import CITY_DATA
from datetime import datetime

ml_bp = Blueprint("ml", __name__)


@ml_bp.route("/ml/predict-risk", methods=["GET"])
def ml_predict_risk():
    """
    Predict income risk score using the weighted feature model.
    Query: ?rainfall=15&aqi=200&hour=14&worker_type=delivery&city=Mumbai
    """
    rainfall    = float(request.args.get("rainfall", 0))
    aqi         = float(request.args.get("aqi", 100))
    hour        = int(request.args.get("hour", datetime.now().hour))
    worker_type = request.args.get("worker_type", "delivery")
    city        = request.args.get("city", "Mumbai")
    user_id     = request.args.get("user_id", "")

    user = users.get(user_id, {})
    if user:
        worker_type = user.get("work_type", worker_type)
        city        = user.get("city", city)

    result = predict_risk(rainfall, aqi, hour, worker_type, city)
    return jsonify({**result, "city": city, "worker_type": worker_type})


@ml_bp.route("/ml/predict-loss", methods=["GET"])
def ml_predict_loss():
    """
    Predict income loss and NexaShift payout for given risk score.
    Query: ?user_id=...  OR  ?income=20000&risk_score=65&work_type=delivery
    """
    user_id  = request.args.get("user_id", "")
    user     = users.get(user_id, {})
    income   = int(request.args.get("income", user.get("income", 20000)))
    risk     = int(request.args.get("risk_score", user.get("risk_score", 60)))
    wtype    = request.args.get("work_type", user.get("work_type", "delivery"))

    result = predict_loss(income, risk, wtype)
    return jsonify(result)


@ml_bp.route("/ml/predict-premium", methods=["GET"])
def ml_predict_premium():
    """
    Dynamic premium calculation for a given risk profile.
    """
    user_id    = request.args.get("user_id", "")
    user       = users.get(user_id, {})
    income     = int(request.args.get("income", user.get("income", 20000)))
    risk       = int(request.args.get("risk_score", user.get("risk_score", 60)))
    consistency = int(request.args.get("consistency", 80))
    city       = request.args.get("city", user.get("city", "Mumbai"))

    result = compute_premium(income, risk, consistency, city)
    return jsonify(result)


@ml_bp.route("/ml/predict-claims-admin", methods=["GET"])
def ml_predict_claims():
    """
    Admin-only: predict tomorrow's claim volume across all cities.
    """
    all_claims_flat = []
    for uc in claims.values():
        all_claims_flat.extend(uc)

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    today_ct  = sum(1 for c in all_claims_flat if c.get("timestamp", "").startswith(today_str))
    flagged   = sum(1 for c in all_claims_flat if c.get("status") == "FLAGGED")
    fraud_rate = flagged / max(len(all_claims_flat), 1)
    avg_risk   = sum(v["base_risk"] for v in CITY_DATA.values()) / len(CITY_DATA)

    result = predict_claims_tomorrow(
        all_claims_today=max(today_ct, 1),
        fraud_rate=fraud_rate,
        avg_risk=avg_risk,
    )
    return jsonify(result)


@ml_bp.route("/ml/explain-risk", methods=["GET"])
def ml_explain_risk():
    """
    Return full feature attribution for current conditions.
    Shows exactly WHY the model produced the risk score.
    """
    user_id     = request.args.get("user_id", "")
    user        = users.get(user_id, {})
    city        = user.get("city", request.args.get("city", "Mumbai"))
    worker_type = user.get("work_type", request.args.get("worker_type", "delivery"))
    income      = user.get("income", int(request.args.get("income", 20000)))

    try:
        from backend.routes.external import get_weather, get_aqi
        weather = get_weather(city)
        aqi     = get_aqi(city)
    except Exception:
        weather = {"rainfall": 5, "temp": 30, "humidity": 65}
        aqi     = 120

    hour     = datetime.now().hour
    rainfall = weather.get("rainfall", 0)

    result = predict_risk(rainfall, aqi, hour, worker_type, city)
    loss   = predict_loss(income, result["risk_score"], worker_type)

    return jsonify({
        **result,
        "loss_prediction": loss,
        "live_inputs": {
            "rainfall":    rainfall,
            "aqi":         aqi,
            "hour":        hour,
            "city":        city,
            "worker_type": worker_type,
        },
    })
