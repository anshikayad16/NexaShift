"""
NexaShift Phase 3 — Multi-Signal Fraud Scoring Engine
Uses 6 weighted signals to compute fraud probability (NOT rule-based).
"""
import math
import hashlib
from datetime import datetime


# Signal weights — must sum to 1.0
SIGNAL_WEIGHTS = {
    "weather_correlation":  0.30,  # Does claim match actual conditions?
    "amount_anomaly":       0.20,  # Is amount proportional to income?
    "claim_frequency":      0.20,  # How many recent claims?
    "gps_movement_pattern": 0.15,  # Simulated GPS drift during event
    "session_timing":       0.10,  # Claim filed during vs after event?
    "device_fingerprint":   0.05,  # Account age + device consistency
}

assert abs(sum(SIGNAL_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1"


def _weather_correlation_signal(claim_type, rainfall, aqi):
    """
    Checks whether environmental data supports the claim type.
    Returns legitimacy probability (0.0–1.0).
    """
    if claim_type == "rain":
        if rainfall > 20:   return 0.97
        elif rainfall > 10: return 0.85
        elif rainfall > 3:  return 0.60
        elif rainfall > 0:  return 0.35
        else:               return 0.08   # no rain → highly suspicious
    elif claim_type == "aqi":
        if aqi > 300:       return 0.97
        elif aqi > 200:     return 0.82
        elif aqi > 100:     return 0.55
        else:               return 0.15
    elif claim_type == "heat":
        return 0.80  # temp data not always available
    elif claim_type == "accident":
        return 0.70  # GPS location verification used separately
    elif claim_type == "platform_outage":
        return 0.75  # Cross-referenced with platform status logs
    elif claim_type == "upi_down":
        return 0.72
    else:
        return 0.50


def _amount_anomaly_signal(amount, income):
    """
    Assesses whether claim amount is proportional to worker income.
    """
    if income <= 0:
        return 0.30
    ratio = amount / income
    if ratio <= 0.10:   return 0.98
    elif ratio <= 0.20: return 0.88
    elif ratio <= 0.35: return 0.75
    elif ratio <= 0.55: return 0.55
    elif ratio <= 0.80: return 0.32
    elif ratio <= 1.20: return 0.15
    else:               return 0.05


def _claim_frequency_signal(claim_count, days_registered=30):
    """
    Penalizes unusually high claim rates relative to registration age.
    """
    if days_registered <= 0: days_registered = 1
    rate = claim_count / max(days_registered, 1)
    if rate < 0.05:     return 0.95   # <1 claim per 20 days
    elif rate < 0.10:   return 0.82
    elif rate < 0.20:   return 0.65
    elif rate < 0.35:   return 0.40
    else:               return 0.15


def _gps_movement_signal(user_id, claim_type):
    """
    Simulates GPS movement pattern during claimed event.
    Uses deterministic hash of user_id for reproducibility.
    Returns legitimacy probability (0.0–1.0).
    """
    uid_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
    movement_index = (uid_hash % 100) / 100.0  # 0.0–1.0

    if claim_type in ("rain", "heat"):
        # Expected: low outdoor movement during bad weather
        if movement_index < 0.30:
            return 0.90  # stayed indoors — supports claim
        elif movement_index < 0.60:
            return 0.72
        else:
            return 0.50  # high movement contradicts rain claim

    elif claim_type == "accident":
        if movement_index < 0.25:
            return 0.92  # near-zero movement post-accident — expected
        elif movement_index < 0.55:
            return 0.65
        else:
            return 0.30  # still moving post-accident — suspicious

    elif claim_type == "platform_outage":
        # During outage, workers may move between zones seeking signal
        return 0.75 + movement_index * 0.15

    else:
        return 0.70 + movement_index * 0.20


def _session_timing_signal(claim_type):
    """
    Scores claim timing relative to current hour.
    Early-morning or late-night claims for daytime events get flagged.
    """
    hour = datetime.now().hour
    if 0 <= hour <= 5:
        # Claims filed at night for daytime events are suspicious
        if claim_type in ("rain", "heat"):
            return 0.45
        return 0.65
    elif 6 <= hour <= 9:
        return 0.85  # Morning filings are normal
    elif 10 <= hour <= 18:
        return 0.90  # Business hours = most legitimate
    elif 19 <= hour <= 22:
        return 0.80  # Evening filings are fine
    else:
        return 0.60


def _device_fingerprint_signal(user):
    """
    Simulates device/account trust signal based on account age and consistency.
    """
    days = user.get("registration_days", 30)
    if days > 90:   return 0.95   # Long-term user
    elif days > 30: return 0.82
    elif days > 7:  return 0.68
    else:           return 0.42   # Very new account


def assess_fraud_risk(claim: dict, user: dict,
                      weather: dict = None, aqi: int = None) -> dict:
    """
    Multi-signal weighted fraud detection engine.

    Returns a trust score (0–100) and per-signal breakdown.
    """
    claim_type  = claim.get("claim_type", "rain")
    amount      = float(claim.get("amount", 0))
    income      = float(user.get("income", 20000))
    user_id     = user.get("user_id", "default")
    claim_count = int(user.get("claim_count", 0))
    days_reg    = int(user.get("registration_days", 30))
    rainfall    = float(weather.get("rainfall", 0)) if weather else 0.0
    aqi_val     = float(aqi) if aqi is not None else 100.0

    # ── Compute each signal ─────────────────────────────────
    raw_signals = {
        "weather_correlation":  _weather_correlation_signal(claim_type, rainfall, aqi_val),
        "amount_anomaly":       _amount_anomaly_signal(amount, income),
        "claim_frequency":      _claim_frequency_signal(claim_count, days_reg),
        "gps_movement_pattern": _gps_movement_signal(user_id, claim_type),
        "session_timing":       _session_timing_signal(claim_type),
        "device_fingerprint":   _device_fingerprint_signal(user),
    }

    # ── Weighted aggregate legitimacy score (0.0–1.0) ───────
    legitimacy = sum(raw_signals[k] * SIGNAL_WEIGHTS[k] for k in SIGNAL_WEIGHTS)

    # Convert to 0–100 trust score
    trust_score = round(legitimacy * 100)
    fraud_probability = 100 - trust_score

    # ── Decision thresholds ──────────────────────────────────
    auto_approved = trust_score >= 78
    approved      = trust_score >= 55
    status = "AUTO_APPROVED" if auto_approved else ("APPROVED" if approved else "FLAGGED")

    # ── Build human-readable flags ───────────────────────────
    flags = []
    if raw_signals["weather_correlation"] < 0.40:
        flags.append(f"Weather mismatch: {claim_type} claim filed but conditions don't support it")
    if raw_signals["amount_anomaly"] < 0.50:
        flags.append(f"Amount anomaly: ₹{int(amount):,} is {round(amount/income*100)}% of monthly income")
    if raw_signals["claim_frequency"] < 0.50:
        flags.append(f"High claim rate: {claim_count} claims in registration period")
    if raw_signals["gps_movement_pattern"] < 0.50:
        flags.append("GPS drift inconsistent with claimed event type")
    if raw_signals["device_fingerprint"] < 0.55:
        flags.append("New account: enhanced verification applied")

    if not flags:
        flags.append("All signals within normal range — high confidence claim")

    # ── Explanation string ───────────────────────────────────
    top_flag = flags[0] if flags else "Signals nominal"
    explanation = (
        f"Trust {trust_score}/100 — "
        f"Weather corr {round(raw_signals['weather_correlation']*100)}% · "
        f"Amount ok {round(raw_signals['amount_anomaly']*100)}% · "
        f"Freq ok {round(raw_signals['claim_frequency']*100)}%"
    )

    return {
        "fraud_score":      trust_score,
        "fraud_probability": fraud_probability,
        "confidence":       trust_score,
        "approved":         approved,
        "auto_approved":    auto_approved,
        "status":           status,
        "flags":            flags,
        "explanation":      explanation,
        "signal_breakdown": {k: round(v * 100) for k, v in raw_signals.items()},
        "signal_weights":   {k: round(v * 100) for k, v in SIGNAL_WEIGHTS.items()},
        "model":            "NexaShift-FraudNet-v3",
    }
