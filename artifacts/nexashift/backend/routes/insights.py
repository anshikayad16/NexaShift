"""
NexaShift Phase 3 — Behavioral Insights API
GET /insights — returns weekly earnings, risk exposure trend, AI explanation
"""
import random
from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users, claims, get_or_rebuild_user
from backend.services.ml_engine import predict_risk, predict_loss
from datetime import datetime

insights_bp = Blueprint("insights", __name__)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

DISRUPTION_IMPACT_PHRASES = [
    ("Rain {rain:.0f}mm/hr caused an estimated {pct:.0f}% drop in daily earnings",         "rain"),
    ("AQI {aqi:.0f} reduced outdoor productivity — projected {pct:.0f}% income impact",    "aqi"),
    ("Heat conditions flagged during {hour}:00 shift — {pct:.0f}% income risk window",     "heat"),
    ("Platform demand dropped — risk model predicts {pct:.0f}% earnings shortfall today",  "generic"),
]


def _weekly_earnings(income: int) -> list:
    daily = income / 26
    week  = []
    seed  = int(income) % 7
    for i in range(7):
        multiplier = 0.72 + (((seed + i * 3) % 17) / 100) * 1.6
        week.append(round(daily * multiplier))
    return week


def _risk_exposure_trend(user_id: str, base_risk: int) -> list:
    trend = []
    for i in range(7):
        jitter = (int(user_id[-2:], 16) if len(user_id) >= 2 and user_id[-2:].isalnum() else 30)
        val = base_risk + ((jitter + i * 7) % 22) - 10
        trend.append(max(10, min(95, val)))
    return trend


def _generate_ai_explanation(weather: dict, aqi: int, risk: int,
                              work_type: str, weekly: list) -> str:
    rainfall = weather.get("rainfall", 0)
    if len(weekly) >= 2:
        diff    = weekly[-1] - weekly[-2]
        pct     = abs(round(diff / max(weekly[-2], 1) * 100))
    else:
        pct = 0

    if rainfall > 15:
        return f"Rain {rainfall:.0f}mm/hr caused an estimated {pct}% drop in daily earnings. NexaShift auto-payout activated."
    elif aqi > 200:
        return f"AQI {aqi} (Hazardous) reduced outdoor productivity — {pct}% income impact detected. Coverage active."
    elif risk > 70:
        return f"Risk score {risk}/100: elevated conditions suppress earnings by ~{pct}%. Shift to safer hours recommended."
    elif pct > 15:
        return f"Earnings variance of {pct}% this week detected. AI suggests peak-hour focus on 7-10AM and 6-9PM windows."
    else:
        return f"Conditions within normal range. Risk {risk}/100 — earnings stable. Continue current work pattern."


@insights_bp.route("/insights", methods=["GET"])
def get_insights():
    user_id = request.args.get("user_id", "")
    user    = get_or_rebuild_user(user_id, request)

    if not user:
        return jsonify({"error": "User not found"}), 404

    city       = user.get("city", "Mumbai")
    work_type  = user.get("work_type", "delivery")
    income     = int(user.get("income", 20000))
    risk_score = int(user.get("risk_score", 55))

    try:
        from backend.routes.external import get_weather, get_aqi
        weather = get_weather(city)
        aqi     = get_aqi(city)
    except Exception:
        weather = {"rainfall": 0, "temp": 30, "humidity": 60}
        aqi     = 100

    rainfall = weather.get("rainfall", 0)
    hour     = datetime.now().hour

    # Weekly earnings simulation
    weekly_earnings = _weekly_earnings(income)

    # Risk exposure trend (past 7 days)
    risk_trend = _risk_exposure_trend(user_id or "default", risk_score)

    # AI explanation
    ai_explanation = _generate_ai_explanation(weather, aqi, risk_score,
                                               work_type, weekly_earnings)

    # Loss model
    ml_loss = predict_loss(income, risk_score, work_type)

    # Risk model
    ml_risk = predict_risk(rainfall, aqi, hour, work_type, city)

    # Claim history stats
    user_claims = claims.get(user_id, [])
    total_claims   = len(user_claims)
    approved_count = sum(1 for c in user_claims if c.get("status") in ("AUTO_APPROVED", "APPROVED"))
    total_payout   = sum(c.get("amount", 0) for c in user_claims if c.get("status") == "AUTO_APPROVED")

    # Weekly recommendations
    recommendations = [
        {
            "text": "Shift 40% of hours to 7–9 AM and 6–8 PM for peak demand windows",
            "impact": f"+12–18% daily income potential",
        },
        {
            "text": f"AQI trending {'high' if aqi > 150 else 'normal'} in {city} — plan indoor alternatives on bad days",
            "impact": f"Avoid ₹{round(income * 0.03 / 26):,} unprotected daily loss",
        },
        {
            "text": (
                f"Risk score {risk_score} is elevated — consider switching to indoor delivery during storms"
                if risk_score > 60 else
                f"Risk score {risk_score} is manageable. Maintain current shift pattern."
            ),
            "impact": "Reduces income volatility by 25%",
        },
        {
            "text": "File claims within 24 hours of a disruption for best approval rates",
            "impact": "Approval rate: 94% on-time vs 76% late",
        },
        {
            "text": "Use Scenario Lab each morning to model conditions before starting your shift",
            "impact": f"Avoid ₹800–1,200 unprotected loss days",
        },
    ]

    # Performance metrics
    approval_rate = round(approved_count / max(total_claims, 1) * 100)
    avg_daily     = round(sum(weekly_earnings) / 7)
    best_day      = max(weekly_earnings)
    worst_day     = min(weekly_earnings)
    trend_dir     = "Upward" if weekly_earnings[-1] > weekly_earnings[0] else "Downward"

    return jsonify({
        "weekly_earnings":      weekly_earnings,
        "days":                 DAYS,
        "risk_exposure_trend":  risk_trend,
        "ai_explanation":       ai_explanation,
        "ml_risk":              ml_risk,
        "ml_loss":              ml_loss,
        "claim_stats": {
            "total_claims":    total_claims,
            "approved_count":  approved_count,
            "total_payout":    total_payout,
            "approval_rate":   approval_rate,
        },
        "performance": {
            "avg_daily_income": avg_daily,
            "best_day":         best_day,
            "worst_day":        worst_day,
            "trend_direction":  trend_dir,
            "weekly_total":     sum(weekly_earnings),
        },
        "recommendations":  recommendations,
        "conditions": {
            "rainfall":    rainfall,
            "aqi":         aqi,
            "temp":        weather.get("temp", 30),
            "hour":        hour,
            "city":        city,
            "risk_score":  risk_score,
        },
    })
