"""
NexaShift Phase 3 — AI Income Autopilot Mode
Generates a personalized 24-hour optimal shift plan based on
real-time conditions + ML risk model.
"""
from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users, autopilot_states, get_or_rebuild_user
from backend.services.ml_engine import predict_risk, predict_loss, DEMAND_MULTIPLIERS
from datetime import datetime

autopilot_bp = Blueprint("autopilot", __name__)

WORK_TYPE_SWITCH_MAP = {
    "delivery": [
        {"type": "grocery_delivery", "label": "Grocery (Instamart/Blinkit)", "reason": "Rain spikes grocery demand 3×"},
        {"type": "pharmacy",         "label": "Pharmacy Delivery",           "reason": "Medical demand is weather-proof"},
    ],
    "rideshare": [
        {"type": "ac_cab",  "label": "AC Premium Cab (Surge)",    "reason": "Surge 2× during bad weather"},
        {"type": "delivery", "label": "Food Delivery Backup",     "reason": "High demand during rain"},
    ],
    "construction": [
        {"type": "domestic_help", "label": "Indoor Helper Services", "reason": "Site shut — earn indoors"},
        {"type": "delivery",      "label": "Part-time Delivery",    "reason": "Flexible, higher income"},
    ],
    "freelance": [
        {"type": "delivery",      "label": "Peak-hour Delivery",   "reason": "Supplement online income"},
    ],
    "domestic_help": [
        {"type": "delivery", "label": "Food Delivery",              "reason": "Higher surge income available"},
    ],
}

ACTION_LABELS = {
    "WORK":     {"color": "#22c55e", "icon": "▶"},
    "OPTIONAL": {"color": "#f59e0b", "icon": "◉"},
    "REST":     {"color": "#f05252", "icon": "■"},
}


def _hourly_risk(hour, weather, aqi, worker_type, city):
    rainfall = weather.get("rainfall", 0)
    result   = predict_risk(rainfall, aqi, hour, worker_type, city)
    return result["risk_score"]


def _hourly_earning(hour, income, risk):
    daily    = income / 26
    hourly   = daily / 10
    demand   = DEMAND_MULTIPLIERS.get(hour, 0.80)
    risk_hit = max(0.3, 1 - risk / 150)
    return round(hourly * demand * risk_hit)


@autopilot_bp.route("/autopilot/plan", methods=["GET"])
def autopilot_plan():
    user_id = request.args.get("user_id", "")
    user    = get_or_rebuild_user(user_id, request)
    if not user:
        return jsonify({"error": "User not found"}), 404

    city        = user.get("city", "Mumbai")
    work_type   = user.get("work_type", "delivery")
    income      = int(user.get("income", 20000))

    try:
        from backend.routes.external import get_weather, get_aqi
        weather = get_weather(city)
        aqi     = get_aqi(city)
    except Exception:
        weather = {"rainfall": 0, "temp": 30, "humidity": 60}
        aqi     = 120

    schedule = []
    for hour in range(6, 23):
        risk    = _hourly_risk(hour, weather, aqi, work_type, city)
        earning = _hourly_earning(hour, income, risk)

        if risk < 40:
            action  = "WORK"
            reason  = f"Low risk ({risk}) + good demand — ideal window"
        elif risk < 65:
            action  = "OPTIONAL"
            reason  = f"Moderate risk ({risk}) — proceed with caution"
        else:
            action  = "REST"
            reason  = f"High risk ({risk}) — NexaShift protection activates if you work"

        schedule.append({
            "hour":              hour,
            "label":             f"{hour}:00",
            "risk":              risk,
            "earning_potential": earning,
            "action":            action,
            "reason":            reason,
            "protection_active": risk > 50,
            "color":             ACTION_LABELS[action]["color"],
            "icon":              ACTION_LABELS[action]["icon"],
        })

    work_slots     = [s for s in schedule if s["action"] == "WORK"]
    optional_slots = [s for s in schedule if s["action"] == "OPTIONAL"]
    rest_slots     = [s for s in schedule if s["action"] == "REST"]

    est_earnings = sum(s["earning_potential"] for s in work_slots)
    est_optional = sum(s["earning_potential"] for s in optional_slots)
    daily_target = round(income / 26)

    # Work-type switch recommendation
    switches   = WORK_TYPE_SWITCH_MAP.get(work_type, [])
    switch_rec = None
    rainfall   = weather.get("rainfall", 0)
    overall_risk = round(sum(s["risk"] for s in schedule) / len(schedule))
    if overall_risk > 50 and switches:
        switch_rec = {
            **switches[0],
            "reason":        switches[0]["reason"],
            "expected_gain": round(daily_target * 0.25),
        }

    peak_hours = [s["hour"] for s in work_slots]

    # Summary narrative
    work_hr_count = len(work_slots)
    if work_hr_count >= 8:
        narrative = (
            f"Excellent earning day predicted. {work_hr_count} safe hours available. "
            f"Focus on {peak_hours[0]}:00–{peak_hours[-1]}:00 for maximum output."
        )
    elif work_hr_count >= 4:
        narrative = (
            f"Partial earning window: {work_hr_count} safe hours. "
            f"NexaShift protection is active during the remaining {len(rest_slots)} high-risk hours."
        )
    else:
        narrative = (
            f"Challenging day ahead. Only {work_hr_count} safe hours — "
            f"NexaShift auto-coverage is activated for high-risk periods."
        )

    # Persist autopilot state
    autopilot_states[user_id] = {
        "enabled": True,
        "activated_at": datetime.utcnow().isoformat(),
        "plan_date": datetime.utcnow().strftime("%Y-%m-%d"),
    }

    return jsonify({
        "schedule":            schedule,
        "optimal_hours":       peak_hours,
        "estimated_earnings":  est_earnings,
        "optional_earnings":   est_optional,
        "daily_target":        daily_target,
        "target_coverage_pct": round(est_earnings / daily_target * 100),
        "overall_risk":        overall_risk,
        "work_hours_count":    work_hr_count,
        "rest_hours_count":    len(rest_slots),
        "switch_recommendation": switch_rec,
        "auto_coverage":       overall_risk > 45,
        "narrative":           narrative,
        "weather_snapshot": {
            "rainfall":    weather.get("rainfall", 0),
            "temp":        weather.get("temp", 30),
            "aqi":         aqi,
        },
        "generated_at": datetime.utcnow().isoformat(),
    })


@autopilot_bp.route("/autopilot/toggle", methods=["POST"])
def autopilot_toggle():
    data    = request.get_json()
    user_id = data.get("user_id")
    enabled = data.get("enabled", True)
    autopilot_states[user_id] = {
        "enabled":      enabled,
        "toggled_at":   datetime.utcnow().isoformat(),
    }
    return jsonify({"status": "ok", "enabled": enabled, "user_id": user_id})


@autopilot_bp.route("/autopilot/status/<user_id>", methods=["GET"])
def autopilot_status(user_id):
    state = autopilot_states.get(user_id, {"enabled": False})
    return jsonify(state)
