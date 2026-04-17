"""
NexaShift Phase 3 — Income Protection Mode
Generates a personalised protection plan based on user profile + live conditions.

Key function: generate_protection_plan(user_data, live_conditions)
Flask blueprint exposes: GET /ai/protection-plan
"""
from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users
from datetime import datetime

protection_bp = Blueprint("protection", __name__)

SAFE_HOUR_WINDOWS = [
    {"start": 6,  "end": 10, "label": "6-10AM",  "reason": "Morning peak demand, lower risk"},
    {"start": 10, "end": 13, "label": "10AM-1PM", "reason": "Moderate demand, manageable risk"},
    {"start": 17, "end": 21, "label": "5-9PM",    "reason": "Evening surge window, high earnings"},
]

AVOID_WINDOWS = [
    {"start": 13, "end": 16, "label": "1-4PM",  "reason": "Midday heat + low demand"},
    {"start": 23, "end": 6,  "label": "11PM-6AM","reason": "Night safety risk"},
]

SWITCH_MAP = {
    "delivery":      ("Switch to grocery delivery (Blinkit/Instamart)",  "Rain spikes grocery demand 3×"),
    "rideshare":     ("Switch to AC cab surge mode",                      "Weather surges premium fares 2×"),
    "construction":  ("Take indoor helper / repair jobs",                  "Site work paused — stay dry, earn indoors"),
    "freelance":     ("Focus on remote/online projects",                   "Zero outdoor exposure, no weather risk"),
    "domestic_help": ("Target covered-complex clients",                    "Prioritise buildings with underground parking"),
}

AI_ACTIONS = [
    "Auto-enable coverage during high-risk window",
    "File pre-emptive claim if rainfall exceeds 15 mm/hr",
    "Trigger income protection when AQI crosses 250",
    "Switch work mode automatically during platform outage",
    "Send push alert before evening storm window",
]


def generate_protection_plan(user_data: dict, live_conditions: dict) -> dict:
    """
    Build a personalised Income Protection Mode plan.

    Inputs:
        user_data        – dict with work_type, income, city, risk_score
        live_conditions  – dict with rainfall, aqi, temp, hour

    Returns structured plan with safe/avoid windows, switch recommendation,
    expected savings, and the AI action that will auto-trigger.
    """
    work_type    = user_data.get("work_type", "delivery")
    income       = float(user_data.get("income", 20000))
    city         = user_data.get("city", "Mumbai")
    risk_score   = int(user_data.get("risk_score", 55))

    rainfall     = float(live_conditions.get("rainfall", 0))
    aqi          = float(live_conditions.get("aqi", 100))
    temp         = float(live_conditions.get("temp", 30))
    hour         = int(live_conditions.get("hour", datetime.now().hour))

    daily_income = income / 26

    # ── Risk-adjusted safe / avoid hours ─────────────────────────
    safe_hours  = []
    avoid_hours = []

    if rainfall > 20 or aqi > 250 or temp > 42:
        safe_hours  = ["7-10AM", "7-9PM"]
        avoid_hours = ["11AM-6PM", "10PM-6AM"]
        risk_window = "HIGH"
    elif rainfall > 10 or aqi > 150 or temp > 38:
        safe_hours  = ["6-10AM", "6-9PM"]
        avoid_hours = ["2-5PM", "11PM-6AM"]
        risk_window = "MODERATE"
    else:
        safe_hours  = ["6-10AM", "12-2PM", "5-9PM"]
        avoid_hours = ["11PM-5AM"]
        risk_window = "LOW"

    # ── Work-type switch recommendation ──────────────────────────
    switch_label, switch_reason = SWITCH_MAP.get(
        work_type, ("Explore alternate gig platforms", "Diversify income sources")
    )

    # ── Expected savings estimate ─────────────────────────────────
    base_loss_rate = (
        0.45 if rainfall > 20 else
        0.30 if rainfall > 10 else
        0.35 if aqi > 250 else
        0.20 if aqi > 150 else
        0.25 if temp > 42 else
        0.15
    )
    daily_loss_unprotected = round(daily_income * base_loss_rate)
    coverage_rate          = 0.85
    expected_savings       = round(daily_loss_unprotected * coverage_rate)

    # ── AI action selection ───────────────────────────────────────
    if rainfall > 15:
        ai_action = "Auto-enable rain coverage — rainfall threshold exceeded"
    elif aqi > 250:
        ai_action = "Trigger AQI income shield — hazardous air quality detected"
    elif temp > 42:
        ai_action = "Activate heat advisory mode — extreme temperature alert"
    elif risk_score > 70:
        ai_action = "Enable elevated-risk coverage mode based on risk score"
    else:
        ai_action = "Monitor conditions — protection ready to auto-activate"

    # ── Coverage recommendation ───────────────────────────────────
    coverage_plan = {
        "rain_coverage":     rainfall > 10,
        "aqi_coverage":      aqi > 150,
        "heat_coverage":     temp > 38,
        "auto_claim_ready":  risk_score > 55 or rainfall > 15,
    }

    # ── Weekly projection ─────────────────────────────────────────
    disruption_days_per_week = (
        4 if risk_window == "HIGH" else
        2 if risk_window == "MODERATE" else 1
    )
    weekly_protected_extra = round(expected_savings * disruption_days_per_week)

    return {
        "risk_window":           risk_window,
        "safe_hours":            safe_hours,
        "avoid_hours":           avoid_hours,
        "recommended_switch":    switch_label,
        "switch_reason":         switch_reason,
        "expected_savings":      expected_savings,
        "weekly_protection":     weekly_protected_extra,
        "ai_action":             ai_action,
        "coverage_plan":         coverage_plan,
        "conditions_snapshot": {
            "rainfall_mm":  rainfall,
            "aqi":          aqi,
            "temp_c":       temp,
            "hour":         hour,
            "city":         city,
        },
        "income_context": {
            "daily_income":      round(daily_income),
            "daily_loss_risk":   daily_loss_unprotected,
            "daily_protected":   expected_savings,
            "protection_rate":   round(coverage_rate * 100),
        },
        "model_version": "NexaShift-ProtectionEngine-v3.0",
        "generated_at":  datetime.utcnow().isoformat(),
    }


@protection_bp.route("/ai/protection-plan", methods=["GET"])
def get_protection_plan():
    """
    GET /ai/protection-plan?user_id=...
    Returns personalised income protection plan using live conditions.
    """
    user_id = request.args.get("user_id", "")

    from backend.utils.memory_store import users as user_store
    user = user_store.get(user_id, {})

    if not user:
        user = {
            "work_type": request.args.get("worker_type", "delivery"),
            "income":    int(request.args.get("income", 20000)),
            "city":      request.args.get("city", "Mumbai"),
            "risk_score": int(request.args.get("risk_score", 55)),
        }

    try:
        from backend.routes.external import get_weather, get_aqi
        city    = user.get("city", "Mumbai")
        weather = get_weather(city)
        aqi     = get_aqi(city)
        live    = {
            "rainfall": weather.get("rainfall", 0),
            "temp":     weather.get("temp", 30),
            "aqi":      aqi,
            "hour":     datetime.now().hour,
        }
    except Exception:
        live = {
            "rainfall": float(request.args.get("rainfall", 0)),
            "temp":     float(request.args.get("temp", 30)),
            "aqi":      float(request.args.get("aqi", 100)),
            "hour":     datetime.now().hour,
        }

    plan = generate_protection_plan(user, live)
    return jsonify(plan)
