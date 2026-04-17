"""
NexaShift Phase 4 — Admin Intelligence Dashboard API
"""
from flask import Blueprint, jsonify, send_from_directory, request
from backend.utils.memory_store import users, claims, payout_logs, fraud_events
from backend.utils.mock_data import CITY_DATA
from backend.services.ml_engine import predict_claims_tomorrow, compute_loss_ratio
import os, random, string
from datetime import datetime, timedelta

admin_bp = Blueprint("admin", __name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WORKER_NAMES = [
    "Ravi Kumar", "Priya Sharma", "Aarav Singh", "Deepa Nair", "Suresh Rao",
    "Anjali Mehta", "Vikram Patel", "Kavya Iyer", "Rohit Verma", "Sunita Devi",
    "Arun Pillai", "Meena Joshi", "Rajesh Gupta", "Lakshmi Rao", "Manish Tiwari",
]
CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Kolkata",
          "Pune", "Ahmedabad", "Jaipur", "Surat", "Nagpur", "Lucknow", "Indore"]

FRAUD_TYPES = [
    {"type": "GPS_ANOMALY", "icon": "📍", "details": [
        "Teleportation detected: 14km in 2 minutes",
        "GPS spoofing: static location despite motion claim",
        "Route trajectory mismatch: claimed highway, GPS shows indoor",
        "Speed anomaly: 0→120km/h instantaneous jump",
        "Zone boundary breach: Claimed Dharavi, GPS shows Andheri",
    ]},
    {"type": "WEATHER_FRAUD", "icon": "🌧", "details": [
        "Weather baseline mismatch: claimed rain 45mm, station shows 0mm",
        "Historical anomaly: clear skies on claimed disruption date",
        "Temporal fraud: rain claim 3hrs after storm ended",
        "Regional mismatch: rain claimed in dry zone per IMD data",
        "Severity inflation: 5mm drizzle claimed as 40mm storm",
    ]},
    {"type": "BEHAVIORAL", "icon": "🧠", "details": [
        "Claim pattern: 3rd rain claim in 7 days",
        "Session anomaly: claim filed during GPS idle state",
        "Device trust score: multiple accounts on same device",
        "Velocity check: claim filed 30s after shift end",
    ]},
]


def _random_id(prefix="FRD"):
    return prefix + "-" + "".join(random.choices(string.digits, k=6))


def _seed_fraud_events():
    if len(fraud_events) >= 5:
        return
    now = datetime.utcnow()
    for i in range(8):
        ft = random.choice(FRAUD_TYPES)
        status = random.choices(["BLOCKED", "FLAGGED", "CLEARED"], weights=[50, 35, 15])[0]
        confidence = round(random.uniform(72, 99), 1)
        ts = (now - timedelta(minutes=random.randint(0, 120))).isoformat()
        fraud_events.append({
            "id": _random_id(),
            "timestamp": ts,
            "type": ft["type"],
            "icon": ft["icon"],
            "worker": random.choice(WORKER_NAMES),
            "city": random.choice(CITIES),
            "amount": random.randint(800, 8500),
            "confidence": confidence,
            "status": status,
            "detail": random.choice(ft["details"]),
            "simulated": False,
        })
    fraud_events.sort(key=lambda x: x["timestamp"])


@admin_bp.route("/admin")
def admin_page():
    return send_from_directory(os.path.join(BASE_DIR, "frontend"), "admin.html")


@admin_bp.route("/admin/stats", methods=["GET"])
def admin_stats():
    _seed_fraud_events()
    all_claims = []
    for uid_claims in claims.values():
        all_claims.extend(uid_claims)

    total_claims  = len(all_claims)
    today_str     = datetime.utcnow().strftime("%Y-%m-%d")
    claims_today  = [c for c in all_claims if c.get("timestamp", "").startswith(today_str)]
    flagged       = [c for c in all_claims if c.get("status") == "FLAGGED"]
    auto_approved = [c for c in all_claims if c.get("status") == "AUTO_APPROVED"]

    fraud_rate = round(len(flagged) / max(total_claims, 1) * 100, 1)
    auto_rate  = round(len(auto_approved) / max(total_claims, 1) * 100, 1)

    total_payouts  = sum(c.get("amount", 0) for c in auto_approved)
    total_users    = len(users)
    total_premiums = sum(u.get("premium", 0) for u in users.values())
    if total_premiums == 0 and total_users > 0:
        total_premiums = sum(round(u.get("income", 20000) * 0.025) for u in users.values())

    loss_ratio_data = compute_loss_ratio(total_payouts, total_premiums)

    city_risks = []
    for city, info in CITY_DATA.items():
        city_claims = [c for c in all_claims if c.get("city") == city]
        city_risks.append({
            "city":         city,
            "base_risk":    info["base_risk"],
            "claims_count": len(city_claims),
            "demand":       info["demand"],
            "lat":          info["lat"],
            "lng":          info["lng"],
        })
    city_risks.sort(key=lambda x: x["base_risk"], reverse=True)

    avg_risk = sum(c["base_risk"] for c in CITY_DATA.values()) / len(CITY_DATA)
    tomorrow = predict_claims_tomorrow(
        all_claims_today=max(len(claims_today), 1),
        fraud_rate=fraud_rate / 100,
        avg_risk=avg_risk,
    )

    type_counts = {}
    for c in all_claims:
        t = c.get("claim_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    payouts_all     = list(payout_logs.values())
    payouts_success = [p for p in payouts_all if p.get("state") == "SUCCESS"]
    payouts_pending = [p for p in payouts_all if p.get("state") not in ("SUCCESS", "FLAGGED")]
    total_paid_out  = sum(p.get("amount", 0) for p in payouts_success)

    # AI confidence from fraud events
    fe_blocked  = [f for f in fraud_events if f["status"] == "BLOCKED"]
    fe_flagged  = [f for f in fraud_events if f["status"] == "FLAGGED"]
    fe_cleared  = [f for f in fraud_events if f["status"] == "CLEARED"]
    avg_conf    = round(
        sum(f["confidence"] for f in fraud_events) / max(len(fraud_events), 1), 1
    )

    # Last fraud detected time
    blocked_sorted = sorted(fe_blocked + fe_flagged, key=lambda x: x["timestamp"], reverse=True)
    last_fraud_ts  = blocked_sorted[0]["timestamp"] if blocked_sorted else None

    return jsonify({
        "timestamp":          datetime.utcnow().isoformat(),
        "total_users":        total_users,
        "total_claims":       total_claims,
        "claims_today":       len(claims_today),
        "auto_approved":      len(auto_approved),
        "flagged":            len(flagged),
        "fraud_rate_pct":     fraud_rate,
        "auto_approval_rate": auto_rate,
        "total_payouts_inr":  total_payouts,
        "total_premiums_inr": total_premiums,
        "loss_ratio":         loss_ratio_data,
        "city_risks":         city_risks,
        "claim_type_breakdown": type_counts,
        "prediction_tomorrow": tomorrow,
        "payout_summary": {
            "total_initiated":  len(payouts_all),
            "total_successful": len(payouts_success),
            "total_pending":    len(payouts_pending),
            "total_paid_inr":   total_paid_out,
        },
        "top_risk_cities":   city_risks[:5],
        "recent_claims":     list(reversed(all_claims[-8:])),
        "ai_decisions": {
            "approved":       len(fe_cleared) + len(auto_approved),
            "blocked":        len(fe_blocked) + len(flagged),
            "under_review":   len(fe_flagged),
            "avg_confidence": avg_conf,
        },
        "system_status": {
            "ai_status":           "ACTIVE",
            "zones_monitored":     65,
            "total_protected_inr": total_payouts + total_paid_out,
            "last_fraud_ts":       last_fraud_ts,
            "fraud_events_total":  len(fraud_events),
        },
    })


@admin_bp.route("/admin/fraud-feed", methods=["GET"])
def fraud_feed():
    _seed_fraud_events()
    limit  = int(request.args.get("limit", 20))
    events = list(reversed(fraud_events[-limit:]))
    now    = datetime.utcnow()

    result = []
    for e in events:
        try:
            ts   = datetime.fromisoformat(e["timestamp"])
            diff = int((now - ts).total_seconds())
            if diff < 60:
                ago = f"{diff}s ago"
            elif diff < 3600:
                ago = f"{diff // 60}m ago"
            else:
                ago = f"{diff // 3600}h ago"
        except Exception:
            ago = "just now"
        result.append({**e, "ago": ago})

    # Latest decision with SHAP-like explanation
    latest = result[0] if result else None
    shap_factors = []
    if latest:
        if latest["type"] == "GPS_ANOMALY":
            shap_factors = [
                {"feature": "GPS trajectory deviation", "score": round(random.uniform(0.28, 0.42), 2), "impact": "high"},
                {"feature": "Speed impossibility index",  "score": round(random.uniform(0.18, 0.30), 2), "impact": "high"},
                {"feature": "Zone boundary mismatch",    "score": round(random.uniform(0.12, 0.22), 2), "impact": "medium"},
                {"feature": "Historical route pattern",  "score": round(random.uniform(0.08, 0.15), 2), "impact": "medium"},
                {"feature": "Device trust score",        "score": round(random.uniform(0.04, 0.10), 2), "impact": "low"},
            ]
        elif latest["type"] == "WEATHER_FRAUD":
            shap_factors = [
                {"feature": "IMD station mismatch",       "score": round(random.uniform(0.30, 0.45), 2), "impact": "high"},
                {"feature": "30-day rainfall baseline",   "score": round(random.uniform(0.20, 0.32), 2), "impact": "high"},
                {"feature": "Temporal claim vs rain end", "score": round(random.uniform(0.12, 0.20), 2), "impact": "medium"},
                {"feature": "Regional weather pattern",   "score": round(random.uniform(0.08, 0.14), 2), "impact": "medium"},
                {"feature": "Claim severity vs reality",  "score": round(random.uniform(0.05, 0.10), 2), "impact": "low"},
            ]
        else:
            shap_factors = [
                {"feature": "Claim velocity (7-day)",    "score": round(random.uniform(0.25, 0.40), 2), "impact": "high"},
                {"feature": "Session timing anomaly",    "score": round(random.uniform(0.18, 0.28), 2), "impact": "high"},
                {"feature": "Device fingerprint match",  "score": round(random.uniform(0.10, 0.20), 2), "impact": "medium"},
                {"feature": "Network pattern analysis",  "score": round(random.uniform(0.08, 0.14), 2), "impact": "medium"},
                {"feature": "Historical claim accuracy", "score": round(random.uniform(0.04, 0.09), 2), "impact": "low"},
            ]

    # Fraud trend (last 12 hours, 1-hour buckets)
    now_hour = now.replace(minute=0, second=0, microsecond=0)
    trend = []
    for i in range(12, 0, -1):
        bucket_start = (now_hour - timedelta(hours=i)).isoformat()
        bucket_end   = (now_hour - timedelta(hours=i - 1)).isoformat()
        bucket_events = [
            e for e in fraud_events
            if bucket_start <= e["timestamp"] < bucket_end
        ]
        blocked_count = len([x for x in bucket_events if x["status"] == "BLOCKED"])
        flagged_count = len([x for x in bucket_events if x["status"] == "FLAGGED"])
        cleared_count = len([x for x in bucket_events if x["status"] == "CLEARED"])
        hour_label = (now_hour - timedelta(hours=i)).strftime("%H:%M")
        trend.append({
            "hour":     hour_label,
            "blocked":  blocked_count + random.randint(0, 2),
            "flagged":  flagged_count + random.randint(0, 1),
            "cleared":  cleared_count + random.randint(0, 3),
        })

    return jsonify({
        "events":      result,
        "shap_factors": shap_factors,
        "latest":      latest,
        "trend":       trend,
        "total":       len(fraud_events),
    })


@admin_bp.route("/admin/simulate-fraud", methods=["POST"])
def simulate_fraud():
    _seed_fraud_events()
    body      = request.get_json(silent=True) or {}
    fraud_type = body.get("type", random.choice(["GPS_ANOMALY", "WEATHER_FRAUD", "BEHAVIORAL"]))

    ft_map = {f["type"]: f for f in FRAUD_TYPES}
    ft     = ft_map.get(fraud_type, FRAUD_TYPES[0])

    status     = random.choices(["BLOCKED", "FLAGGED"], weights=[70, 30])[0]
    confidence = round(random.uniform(85, 99), 1)
    worker     = random.choice(WORKER_NAMES)
    city       = random.choice(CITIES)
    amount     = random.randint(1500, 9500)

    event = {
        "id":         _random_id("SIM"),
        "timestamp":  datetime.utcnow().isoformat(),
        "type":       ft["type"],
        "icon":       ft["icon"],
        "worker":     worker,
        "city":       city,
        "amount":     amount,
        "confidence": confidence,
        "status":     status,
        "detail":     random.choice(ft["details"]),
        "simulated":  True,
    }

    fraud_events.append(event)
    if len(fraud_events) > 200:
        fraud_events.pop(0)

    return jsonify({"success": True, "event": event})


@admin_bp.route("/admin/metrics", methods=["GET"])
def admin_metrics():
    all_claims = []
    for uid_claims in claims.values():
        all_claims.extend(uid_claims)

    total_claims  = len(all_claims)
    flagged       = [c for c in all_claims if c.get("status") == "FLAGGED"]
    auto_approved = [c for c in all_claims if c.get("status") == "AUTO_APPROVED"]

    total_payouts  = sum(c.get("amount", 0) for c in auto_approved)
    total_premiums = sum(u.get("premium", 0) for u in users.values())
    if total_premiums == 0 and len(users) > 0:
        total_premiums = sum(round(u.get("income", 20000) * 0.025) for u in users.values())

    loss_ratio_data = compute_loss_ratio(total_payouts, total_premiums)

    from backend.services.ml_engine import compute_premium
    premium_adjustments = []
    for city_name, info in CITY_DATA.items():
        base_risk     = info["base_risk"]
        sample_income = 22000
        pm            = compute_premium(sample_income, base_risk, 80, city_name)
        change_val    = round((pm["risk_multiplier"] - 1.0) * pm["monthly_premium"])
        premium_adjustments.append({
            "city":              city_name,
            "risk_score":        base_risk,
            "next_week_premium": pm["monthly_premium"],
            "change":            f"+{change_val}" if change_val >= 0 else str(change_val),
            "change_int":        change_val,
            "reason":            (
                "High risk profile + elevated weather exposure"
                if base_risk > 65 else
                "Moderate risk — stable premium"
                if base_risk > 50 else
                "Below-average risk — discounted premium"
            ),
            "location_factor": pm["location_factor"],
        })
    premium_adjustments.sort(key=lambda x: x["risk_score"], reverse=True)

    gps_flags      = len([c for c in flagged if "GPS" in " ".join(c.get("flags", []))])
    weather_mis    = len([c for c in flagged if "Weather" in " ".join(c.get("flags", []))])
    behavior_flags = len(flagged) - gps_flags - weather_mis

    total_blocked_amount = sum(c.get("amount", 0) for c in flagged)
    fraud_summary = {
        "total_flagged":          len(flagged),
        "total_blocked_inr":      total_blocked_amount,
        "gps_flags":              max(gps_flags, 0),
        "weather_mismatch":       max(weather_mis, 0),
        "behavior_flags":         max(behavior_flags, 0),
        "fraud_rate_pct":         round(len(flagged) / max(total_claims, 1) * 100, 1),
        "auto_approval_rate_pct": round(len(auto_approved) / max(total_claims, 1) * 100, 1),
        "model":                  "NexaShift-FraudNet-v3",
    }

    city_risk_claims = []
    for city_name, info in CITY_DATA.items():
        city_claims = [c for c in all_claims if c.get("city") == city_name]
        city_risk_claims.append({
            "city":         city_name,
            "risk_score":   info["base_risk"],
            "claims_count": len(city_claims),
            "demand":       info["demand"],
            "avg_payout":   info["avg_payout"],
            "lat":          info["lat"],
            "lng":          info["lng"],
        })
    city_risk_claims.sort(key=lambda x: x["risk_score"], reverse=True)

    payouts_all     = list(payout_logs.values())
    payouts_success = [p for p in payouts_all if p.get("state") == "SUCCESS"]
    total_paid_out  = sum(p.get("amount", 0) for p in payouts_success)

    return jsonify({
        "timestamp":           datetime.utcnow().isoformat(),
        "loss_ratio":          loss_ratio_data,
        "premium_adjustments": premium_adjustments,
        "fraud_summary":       fraud_summary,
        "city_risk_claims":    city_risk_claims,
        "payout_pipeline": {
            "total_initiated":  len(payouts_all),
            "total_successful": len(payouts_success),
            "total_paid_inr":   total_paid_out,
        },
        "totals": {
            "users":         len(users),
            "claims":        total_claims,
            "auto_approved": len(auto_approved),
            "flagged":       len(flagged),
            "payouts_inr":   total_payouts,
            "premiums_inr":  total_premiums,
        },
    })
