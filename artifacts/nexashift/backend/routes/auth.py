from flask import Blueprint, request, jsonify
from backend.services.risk_engine import compute_risk_score
from backend.services.pricing_engine import compute_premium, compute_coverage
from backend.utils.memory_store import users
import uuid

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = data.get("name", "").strip()
    city = data.get("city", "Mumbai").strip()
    income = int(data.get("income", 15000))
    work_type = data.get("work_type", "delivery")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    try:
        from backend.routes.external import get_weather, get_aqi
        weather = get_weather(city)
        aqi = get_aqi(city)
    except Exception:
        weather = {}
        aqi = 100

    user_id = str(uuid.uuid4())
    risk_score = compute_risk_score(city, work_type, income, weather=weather, aqi=aqi)
    premium = compute_premium(income, risk_score)
    coverage = compute_coverage(income)

    user = {
        "user_id": user_id,
        "name": name,
        "city": city,
        "income": income,
        "work_type": work_type,
        "risk_score": risk_score,
        "premium": premium,
        "coverage": coverage,
        "claim_count": 0,
        "weather": weather,
        "aqi": aqi,
    }
    users[user_id] = user

    return jsonify({
        "user_id": user_id,
        "name": name,
        "city": city,
        "income": income,
        "work_type": work_type,
        "risk_score": risk_score,
        "premium": premium,
        "coverage": coverage,
        "message": (
            f"Welcome {name}! Your income protection policy is active. "
            f"Risk score: {risk_score}/100. "
            f"Weather: {weather.get('description', 'N/A')}, AQI: {aqi}."
        ),
    }), 201


@auth_bp.route("/restore-session", methods=["POST"])
def restore_session():
    """
    Re-hydrate a user into in-memory store from their localStorage profile.
    Called on frontend boot when a saved session exists but the backend
    restarted (in-memory store wiped).
    """
    data = request.get_json()
    if not data or not data.get("user_id"):
        return jsonify({"error": "No session data"}), 400

    user_id = data["user_id"]

    # If user is already in memory (normal case), return immediately
    if user_id in users:
        return jsonify({"status": "ok", "restored": False, "user": users[user_id]})

    # Rebuild user record from the saved frontend profile
    name      = data.get("name", "Worker")
    city      = data.get("city", "Mumbai")
    income    = int(data.get("income", 20000))
    work_type = data.get("work_type", "delivery")

    try:
        from backend.routes.external import get_weather, get_aqi
        weather = get_weather(city)
        aqi     = get_aqi(city)
    except Exception:
        weather = {}
        aqi     = 100

    risk_score = compute_risk_score(city, work_type, income, weather=weather, aqi=aqi)
    premium    = compute_premium(income, risk_score)
    coverage   = compute_coverage(income)

    user = {
        "user_id":    user_id,
        "name":       name,
        "city":       city,
        "income":     income,
        "work_type":  work_type,
        "risk_score": risk_score,
        "premium":    premium,
        "coverage":   coverage,
        "claim_count": 0,
        "weather":    weather,
        "aqi":        aqi,
    }
    users[user_id] = user

    return jsonify({"status": "ok", "restored": True, "user": user})


@auth_bp.route("/users", methods=["GET"])
def list_users():
    return jsonify(list(users.values()))
