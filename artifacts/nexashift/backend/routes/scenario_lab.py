from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users
import math

scenario_lab_bp = Blueprint("scenario_lab", __name__)

WORK_SWITCH_OPTIONS = {
    "delivery": [
        {"to": "grocery_delivery", "label": "Grocery Delivery (Instamart)", "gain_pct": 0.40, "reason": "Rain spikes grocery demand 3x"},
        {"to": "pharmacy_delivery", "label": "Pharmacy Delivery", "gain_pct": 0.25, "reason": "Medical deliveries not weather-impacted"},
        {"to": "freelance", "label": "Online Freelance", "gain_pct": 0.10, "reason": "Indoor work, zero weather risk"},
    ],
    "rideshare": [
        {"to": "delivery", "label": "Food Delivery (Swiggy/Zomato)", "gain_pct": 0.35, "reason": "High demand during rain"},
        {"to": "ac_cab", "label": "AC Premium Cab (Surge Active)", "gain_pct": 0.50, "reason": "Surge pricing 2x during bad weather"},
        {"to": "freelance", "label": "Online Freelance", "gain_pct": 0.05, "reason": "Indoor work as backup"},
    ],
    "construction": [
        {"to": "delivery", "label": "Delivery Work", "gain_pct": 0.20, "reason": "Can earn while site is shut"},
        {"to": "domestic_help", "label": "Indoor Helper Services", "gain_pct": 0.15, "reason": "Indoor, weather-safe"},
        {"to": "freelance", "label": "Skilled Labour Gigs Online", "gain_pct": 0.10, "reason": "Remote consultancy"},
    ],
    "freelance": [
        {"to": "delivery", "label": "Part-time Delivery", "gain_pct": 0.30, "reason": "Extra income during high-demand periods"},
        {"to": "domestic_help", "label": "Home Services", "gain_pct": 0.15, "reason": "Steady indoor work"},
    ],
    "domestic_help": [
        {"to": "delivery", "label": "Food Delivery", "gain_pct": 0.25, "reason": "High surge income available"},
        {"to": "freelance", "label": "Online Micro-tasks", "gain_pct": 0.10, "reason": "Home-based, risk-free"},
    ],
}


def compute_risk_from_sliders(rain_mm, aqi, hour):
    rain_risk = min(100, rain_mm * 3.5)
    aqi_risk = min(100, max(0, (aqi - 50) / 4.5))
    time_risk = 0
    if 22 <= hour or hour < 5:
        time_risk = 30
    elif 7 <= hour <= 10 or 17 <= hour <= 20:
        time_risk = 15

    risk = round(rain_risk * 0.5 + aqi_risk * 0.3 + time_risk * 0.2)
    return min(100, max(0, risk))


def income_projection_by_hour(base_daily, rain_mm, aqi, hour):
    hourly_base = base_daily / 10
    demand_mult = {
        7: 1.4, 8: 1.6, 9: 1.3, 10: 1.0, 11: 0.7, 12: 1.2,
        13: 1.1, 14: 0.8, 15: 0.7, 16: 0.9, 17: 1.5, 18: 1.8,
        19: 1.6, 20: 1.3, 21: 1.0, 22: 0.6
    }.get(hour, 0.8)

    rain_mult = max(0.3, 1.0 - rain_mm * 0.028)
    aqi_mult = max(0.6, 1.0 - max(0, aqi - 100) * 0.001)
    return round(hourly_base * demand_mult * rain_mult * aqi_mult)


@scenario_lab_bp.route("/scenario-lab", methods=["GET"])
def scenario_lab():
    user_id = request.args.get("user_id", "")
    rain_mm = float(request.args.get("rain", 0))
    aqi = float(request.args.get("aqi", 100))
    hour = int(request.args.get("hour", 12))

    user = users.get(user_id, {})
    base_income = int(user.get("income", 20000))
    work_type = user.get("work_type", "delivery")
    base_daily = round(base_income / 26)

    risk = compute_risk_from_sliders(rain_mm, aqi, hour)

    projections = []
    for h in range(6, 23):
        projected = income_projection_by_hour(base_daily, rain_mm, aqi, h)
        protected = round(projected * (1 + 0.15)) if h == hour else projected
        projections.append({
            "hour": h,
            "label": f"{h}:00",
            "income": projected,
            "protected": protected,
        })

    rain_drop = round(min(0.70, rain_mm * 0.028) * 100)
    aqi_drop = round(min(0.40, max(0, aqi - 100) * 0.001) * 100)
    total_drop = min(85, rain_drop + aqi_drop)
    daily_loss = round(base_daily * total_drop / 100)
    payout = round(daily_loss * 0.85) if total_drop > 15 else 0

    time_label = f"{hour}:00 {'AM' if hour < 12 else 'PM'}"
    if hour == 0:
        time_label = "12:00 AM"
    elif hour < 12:
        time_label = f"{hour}:00 AM"
    elif hour == 12:
        time_label = "12:00 PM"
    else:
        time_label = f"{hour - 12}:00 PM"

    if rain_mm > 15 and aqi > 200:
        recommendation = f"CRITICAL: Extreme conditions. Stop outdoor work immediately. Expected NexaShift payout: ₹{payout:,}"
        rec_level = "critical"
    elif rain_mm > 8 or aqi > 150:
        recommendation = f"HIGH RISK: Reduce outdoor hours by 60%. File preemptive claim. Protection covers ₹{payout:,}"
        rec_level = "warning"
    elif risk > 30:
        recommendation = f"MODERATE RISK: Monitor conditions. Income drop ~{total_drop}%. Take indoor orders."
        rec_level = "moderate"
    else:
        recommendation = f"LOW RISK: Conditions are safe. Best earning window at current time ({time_label})."
        rec_level = "safe"

    switches = WORK_SWITCH_OPTIONS.get(work_type, WORK_SWITCH_OPTIONS["delivery"])
    auto_switch = None
    if risk > 40:
        best = switches[0]
        gain = round(base_daily * best["gain_pct"])
        auto_switch = {
            "from": work_type,
            "to": best["to"],
            "label": best["label"],
            "expected_gain": gain,
            "reason": best["reason"],
        }

    return jsonify({
        "risk": risk,
        "rain_mm": rain_mm,
        "aqi": aqi,
        "hour": hour,
        "time_label": time_label,
        "base_daily": base_daily,
        "estimated_loss": daily_loss,
        "payout": payout,
        "income_drop_pct": total_drop,
        "projections": projections,
        "recommendation": recommendation,
        "rec_level": rec_level,
        "auto_switch": auto_switch,
        "without_nexashift": base_daily - daily_loss,
        "with_nexashift": base_daily - daily_loss + payout,
    })
