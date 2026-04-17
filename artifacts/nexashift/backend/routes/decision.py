import random
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users
from backend.services.decision_engine import get_daily_plan
from backend.services.risk_engine import compute_risk_score, compute_weather_risk_factor
from backend.services.explain_engine import explain_decision

decision_bp = Blueprint("decision", __name__)


def _get_weather_and_aqi(city: str):
    from backend.routes.external import get_weather, get_aqi
    weather = get_weather(city)
    aqi = get_aqi(city)
    return weather, aqi


@decision_bp.route("/live-decision/<user_id>", methods=["GET"])
def live_decision(user_id):
    user = users.get(user_id)
    if not user:
        city = request.args.get("city", "Mumbai")
        work_type = request.args.get("work_type", "delivery")
        income = int(request.args.get("income", 20000))
        user = {"city": city, "work_type": work_type, "income": income, "risk_score": 60}

    city = user.get("city", "Mumbai")
    work_type = user.get("work_type", "delivery")
    income = user.get("income", 20000)

    weather, aqi = _get_weather_and_aqi(city)
    risk_score = compute_risk_score(city, work_type, income, weather=weather, aqi=aqi)
    risk_factor = compute_weather_risk_factor(weather, aqi)

    hour = datetime.now().hour
    rainfall = weather.get("rainfall", 0)
    temp = weather.get("temp", 28)

    surge_active = (9 <= hour <= 11) or (18 <= hour <= 21)
    rain_heavy = rainfall > 15
    aqi_high = aqi > 250

    base_hourly = income / (26 * 8)

    if surge_active:
        base_hourly *= 1.4
    if rain_heavy:
        base_hourly *= 0.55
    elif rainfall > 5:
        base_hourly *= 0.78
    if aqi_high:
        base_hourly *= 0.85
    if temp > 42:
        base_hourly *= 0.80

    expected_hourly = round(base_hourly * random.uniform(0.92, 1.08))

    if risk_score > 75 or (rain_heavy and aqi_high):
        recommendation = "STOP"
        action = "STOP — Conditions too risky. File a weather claim for income protection."
        color = "danger"
    elif risk_score > 55 or rain_heavy or aqi_high:
        recommendation = "CAUTION"
        action = "PROCEED WITH CAUTION — Risk elevated. Check for surge zones before going out."
        color = "warning"
    else:
        recommendation = "GO"
        action = "GO ONLINE NOW — Conditions are favorable. Surge demand detected."
        color = "success"

    reasons = []
    if rain_heavy:
        reasons.append(f"Heavy rain ({rainfall}mm/hr) reducing order flow")
    elif rainfall > 5:
        reasons.append(f"Light rain ({rainfall}mm/hr) — some orders impacted")
    if aqi_high:
        reasons.append(f"AQI {aqi} — outdoor health risk")
    if surge_active:
        reasons.append(f"Surge window: {hour}:00 hrs — peak demand")
    if temp > 38:
        reasons.append(f"High temp ({temp}°C) — physical strain risk")
    if not reasons:
        reasons.append("Normal conditions — standard risk profile")

    upcoming_risk = []
    if 6 <= hour <= 10:
        upcoming_risk.append("Peak heat expected 12–15 hrs")
    if datetime.now().weekday() == 4:
        upcoming_risk.append("Friday evening surge in 2–3 hrs")
    if rainfall < 2 and random.random() < 0.25:
        upcoming_risk.append("Rain probability 40% in next 3 hours")

    advice_map = {
        "delivery": {
            "GO": "Focus on high-value restaurant zones. Avoid waterlogged roads.",
            "CAUTION": "Switch to grocery delivery — rain spikes demand 3x.",
            "STOP": "File weather claim. Consider indoor task platforms (UrbanClap).",
        },
        "rideshare": {
            "GO": "Airport and station pickups most profitable now.",
            "CAUTION": "Surge pricing active. Accept rides from drier zones.",
            "STOP": "Pause outdoor rides. Drive to a covered area and rest.",
        },
        "construction": {
            "GO": "Site conditions safe. Maximize hours.",
            "CAUTION": "Check scaffolding safety. Avoid wet surface areas.",
            "STOP": "Do NOT work in rain/lightning. File construction halt claim.",
        },
    }
    advice = advice_map.get(work_type, {}).get(recommendation, "Monitor conditions and stay safe.")

    auto_triggered = False
    payout_triggered = 0
    if rain_heavy or (rainfall > 10 and aqi_high):
        auto_triggered = True
        payout_triggered = round(income * 0.15 * random.uniform(0.8, 1.2))

    return jsonify({
        "recommendation": recommendation,
        "action": action,
        "color": color,
        "expected_earnings_next_hour": expected_hourly,
        "risk_score": risk_score,
        "reasons": reasons,
        "upcoming_risk": upcoming_risk,
        "advice": advice,
        "weather": weather,
        "aqi": aqi,
        "auto_trigger_fired": auto_triggered,
        "payout_triggered": payout_triggered if auto_triggered else 0,
        "surge_active": surge_active,
        "timestamp": datetime.now().isoformat(),
        "next_check_in": 10,
    })


@decision_bp.route("/daily-plan/<user_id>", methods=["GET"])
def daily_plan(user_id):
    user = users.get(user_id)
    if not user:
        user = {
            "city": request.args.get("city", "Mumbai"),
            "work_type": request.args.get("work_type", "delivery"),
            "income": int(request.args.get("income", 20000)),
            "risk_score": 60,
        }
    weather, aqi = _get_weather_and_aqi(user.get("city", "Mumbai"))
    user["weather"] = weather
    user["aqi"] = aqi
    plan = get_daily_plan(user)
    return jsonify(plan)


@decision_bp.route("/dashboard/summary", methods=["GET"])
def dashboard_summary():
    user_id = request.args.get("user_id")
    user = users.get(user_id, {})

    income = user.get("income", 20000)
    risk_score = user.get("risk_score", 60)
    city = user.get("city", "Mumbai")

    try:
        weather, aqi = _get_weather_and_aqi(city)
        live_risk = compute_risk_score(city, user.get("work_type", "delivery"), income, weather=weather, aqi=aqi)
        user["risk_score"] = live_risk
        risk_score = live_risk
    except Exception:
        weather = {}
        aqi = 100

    weekly_earnings = []
    for i in range(7):
        variation = random.uniform(0.75, 1.25)
        weekly_earnings.append(round(income / 4 * variation))

    return jsonify({
        "user_id": user_id,
        "name": user.get("name", "Gig Worker"),
        "monthly_income": income,
        "risk_score": risk_score,
        "coverage": user.get("coverage", income * 3),
        "premium": user.get("premium", 0),
        "claim_count": user.get("claim_count", 0),
        "city": city,
        "work_type": user.get("work_type", "delivery"),
        "weekly_earnings": weekly_earnings,
        "weather": weather,
        "aqi": aqi,
    })


@decision_bp.route("/ai/explain", methods=["GET"])
def ai_explain():
    event = request.args.get("event", "rain")
    user_id = request.args.get("user_id")
    user = users.get(user_id, {})
    city = user.get("city", "Mumbai")
    work_type = user.get("work_type", "delivery")

    try:
        weather, aqi = _get_weather_and_aqi(city)
    except Exception:
        weather = {"rainfall": 12, "temp": 30, "humidity": 80}
        aqi = 180

    from backend.services.explain_engine import explain_risk
    hour = datetime.now().hour
    return jsonify(explain_risk(event, weather, aqi, hour, city, work_type))
