from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users, claims, get_or_rebuild_user
from backend.services.fraud_engine import assess_fraud_risk
from backend.services.payout_engine import initiate_payout
import uuid
from datetime import datetime

claim_bp = Blueprint("claim", __name__)


@claim_bp.route("/claim/process", methods=["POST"])
def process_claim():
    data       = request.get_json()
    user_id    = data.get("user_id")
    claim_type = data.get("claim_type", "rain")
    amount     = int(data.get("amount", 3000))
    description = data.get("description", "")

    user = get_or_rebuild_user(user_id, request)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        from backend.routes.external import get_weather, get_aqi
        weather  = get_weather(user.get("city", "Mumbai"))
        aqi      = get_aqi(user.get("city", "Mumbai"))
        rainfall = weather.get("rainfall", 0)
    except Exception:
        weather  = {}
        aqi      = 100
        rainfall = 0

    # Smart payout calculation
    if claim_type == "rain" and rainfall > 10:
        auto_payout = round(amount * min(1.1, 0.9 + rainfall / 100))
    elif claim_type == "aqi" and aqi > 250:
        auto_payout = round(amount * 0.90)
    else:
        auto_payout = amount

    # Multi-signal fraud engine (Phase 3)
    fraud_result = assess_fraud_risk(
        {"claim_type": claim_type, "amount": auto_payout},
        user,
        weather=weather,
        aqi=aqi,
    )

    claim_id = str(uuid.uuid4())[:8].upper()

    # Build rich explanation
    if claim_type == "rain" and rainfall > 5:
        explanation = (
            f"Rain {rainfall}mm/hr → {round(rainfall * 1.5)}% income drop detected. "
            f"Weather corr score {fraud_result['signal_breakdown'].get('weather_correlation',0)}%."
        )
    elif claim_type == "aqi" and aqi > 150:
        explanation = (
            f"AQI {aqi} → outdoor work impact confirmed. "
            f"Weather corr score {fraud_result['signal_breakdown'].get('weather_correlation',0)}%."
        )
    else:
        explanation = fraud_result.get("explanation", "Standard claim assessment complete.")

    claim = {
        "claim_id":         claim_id,
        "user_id":          user_id,
        "city":             user.get("city", "Mumbai"),
        "claim_type":       claim_type,
        "amount":           auto_payout,
        "description":      description,
        "status":           fraud_result["status"],
        "fraud_score":      fraud_result["fraud_score"],
        "auto_approved":    fraud_result["auto_approved"],
        "flags":            fraud_result["flags"],
        "signal_breakdown": fraud_result.get("signal_breakdown", {}),
        "weather_snapshot": {"rainfall": rainfall, "aqi": aqi},
        "timestamp":        datetime.utcnow().isoformat(),
        "explanation":      explanation,
    }

    if user_id not in claims:
        claims[user_id] = []
    claims[user_id].append(claim)
    user["claim_count"] = user.get("claim_count", 0) + 1

    # Initiate UPI payout if auto-approved
    payout_obj = None
    if fraud_result["auto_approved"]:
        payout_obj = initiate_payout(claim_id, auto_payout, user)

    return jsonify({
        "claim_id":         claim_id,
        "status":           fraud_result["status"],
        "fraud_score":      fraud_result["fraud_score"],
        "fraud_probability": fraud_result.get("fraud_probability", 0),
        "auto_approved":    fraud_result["auto_approved"],
        "approved_amount":  auto_payout if fraud_result["approved"] else 0,
        "flags":            fraud_result["flags"],
        "signal_breakdown": fraud_result.get("signal_breakdown", {}),
        "signal_weights":   fraud_result.get("signal_weights", {}),
        "explanation":      explanation,
        "payout":           payout_obj,
        "message": (
            f"✅ Claim {claim_id} AUTO-APPROVED! ₹{auto_payout:,} initiating UPI transfer. {explanation}"
            if fraud_result["auto_approved"]
            else f"⏳ Claim {claim_id} under review. Expected resolution in 24 hrs."
        ),
        "timestamp": claim["timestamp"],
    })


@claim_bp.route("/claims/<user_id>", methods=["GET"])
def get_claims(user_id):
    return jsonify(claims.get(user_id, []))
