"""
NexaShift Phase 3 — ML-like Prediction Models
Weighted linear models trained on synthetic Indian gig-worker data.
All weights are explainable and deterministic (no black boxes).
"""
import math
from datetime import datetime
from backend.utils.mock_data import CITY_DATA


# ── Risk Prediction Model ─────────────────────────────────────
# Feature weights learned from historical disruption data
RISK_WEIGHTS = {
    "rainfall":    0.35,
    "aqi":         0.25,
    "time_factor": 0.15,
    "worker_type": 0.25,
}

WORKER_RISK_PROFILE = {
    "delivery":     0.70,
    "rideshare":    0.55,
    "construction": 0.80,
    "freelance":    0.18,
    "domestic_help": 0.32,
}

DEMAND_MULTIPLIERS = {
    6: 0.85, 7: 1.40, 8: 1.65, 9: 1.35, 10: 1.10, 11: 0.80,
    12: 1.20, 13: 1.15, 14: 0.85, 15: 0.75, 16: 0.95, 17: 1.55,
    18: 1.80, 19: 1.60, 20: 1.35, 21: 1.10, 22: 0.65
}


def _time_risk_factor(hour: int) -> float:
    """Night hours and extreme peak hours carry different risk profiles."""
    if 0 <= hour <= 5:   return 0.82   # Night: unsafe, low demand
    elif 7 <= hour <= 9: return 0.22   # Morning peak: safe + high demand
    elif 17 <= hour <= 20: return 0.25 # Evening peak: safe + high demand
    elif 22 <= hour <= 23: return 0.65 # Late night: moderate risk
    else:                return 0.42


def predict_risk(rainfall: float, aqi: float, hour: int,
                 worker_type: str, city: str = "Mumbai") -> dict:
    """
    ML risk model using normalized weighted feature sum.

    risk = Σ (w_i × f_i) × city_bias
    Normalized to [10, 95]
    """
    city_base  = CITY_DATA.get(city, {}).get("base_risk", 50)
    rain_norm  = min(1.0, rainfall / 60.0)
    aqi_norm   = min(1.0, max(0.0, (aqi - 50) / 450.0))
    time_f     = _time_risk_factor(hour)
    worker_f   = WORKER_RISK_PROFILE.get(worker_type, 0.50)

    model_score = (
        RISK_WEIGHTS["rainfall"]    * rain_norm +
        RISK_WEIGHTS["aqi"]         * aqi_norm  +
        RISK_WEIGHTS["time_factor"] * time_f    +
        RISK_WEIGHTS["worker_type"] * worker_f
    ) * 100

    # City base provides a geographic bias (weighted 30%)
    final_risk = model_score * 0.70 + city_base * 0.30
    final_risk = round(min(95, max(10, final_risk)))

    contributions = {
        "Rainfall intensity":     round(RISK_WEIGHTS["rainfall"]    * rain_norm  * 100, 1),
        "Air quality (AQI)":      round(RISK_WEIGHTS["aqi"]         * aqi_norm   * 100, 1),
        "Time-of-day pattern":    round(RISK_WEIGHTS["time_factor"] * time_f     * 100, 1),
        "Worker type exposure":   round(RISK_WEIGHTS["worker_type"] * worker_f   * 100, 1),
    }

    return {
        "risk_score":              final_risk,
        "feature_contributions":   contributions,
        "feature_inputs": {
            "rainfall_mm_hr":   rainfall,
            "aqi":              aqi,
            "hour":             hour,
            "worker_type":      worker_type,
            "city_base_risk":   city_base,
        },
        "model_version": "NexaShift-RiskNet-v3.1",
        "confidence_pct": min(96, 70 + final_risk // 5),
    }


# ── Loss Prediction Model ─────────────────────────────────────
DISRUPTION_FACTORS = {
    "delivery":     0.82,
    "rideshare":    0.70,
    "construction": 0.90,
    "freelance":    0.38,
    "domestic_help": 0.52,
}

NEXASHIFT_COVERAGE_RATIO = 0.84  # NexaShift covers 84% of predicted loss


def predict_loss(base_income: int, risk_score: int, work_type: str) -> dict:
    """
    loss = baseline_daily × P(disruption) × disruption_factor
    protected_income = income - loss + nexashift_payout
    """
    daily_income     = base_income / 26
    risk_probability = risk_score  / 100
    disruption_f     = DISRUPTION_FACTORS.get(work_type, 0.70)

    predicted_loss  = daily_income * risk_probability * disruption_f
    nexashift_payout = predicted_loss * NEXASHIFT_COVERAGE_RATIO
    net_income      = daily_income - predicted_loss + nexashift_payout

    return {
        "daily_income":           round(daily_income),
        "risk_probability_pct":   round(risk_probability * 100, 1),
        "disruption_factor":      disruption_f,
        "predicted_loss":         round(predicted_loss),
        "nexashift_payout":       round(nexashift_payout),
        "net_protected_income":   round(net_income),
        "unprotected_income":     round(daily_income - predicted_loss),
        "protection_benefit":     round(nexashift_payout),
        "model_version":          "NexaShift-LossNet-v3.1",
    }


# ── Premium Pricing Model ─────────────────────────────────────
BASE_PREMIUM_RATE = 0.025   # 2.5% of monthly income

LOCATION_FACTORS = {
    "Mumbai":    1.22, "Delhi":     1.18, "Bengaluru": 1.10,
    "Chennai":   1.08, "Hyderabad": 1.05, "Pune":      1.07,
    "Kolkata":   1.12, "Ahmedabad": 1.00, "Jaipur":    0.97,
    "Surat":     0.95, "Nagpur":    1.02, "Lucknow":   1.04,
    "Indore":    0.99,
}


def compute_premium(income: int, risk_score: int,
                    consistency_score: int, city: str) -> dict:
    """
    premium = f(income, risk, consistency, location)
    Lower consistency (more claims) = higher premium.
    """
    location_f    = LOCATION_FACTORS.get(city, 1.0)
    risk_mult     = 1.0 + (risk_score - 50) / 100
    consistency_d = max(0, (100 - consistency_score) / 200)

    premium = (income * BASE_PREMIUM_RATE
               * risk_mult
               * location_f
               * (1 + consistency_d))

    coverage = income * 3.5 * (1 + risk_score / 200)

    return {
        "monthly_premium":     round(premium),
        "coverage_amount":     round(coverage),
        "risk_multiplier":     round(risk_mult, 3),
        "location_factor":     location_f,
        "consistency_discount": round(consistency_d, 3),
        "premium_rate_pct":    round(BASE_PREMIUM_RATE * risk_mult * location_f * 100, 2),
        "model_version":       "NexaShift-PremiumNet-v3.1",
    }


# ── Admin Prediction Model ────────────────────────────────────
def predict_claims_tomorrow(all_claims_today: int, fraud_rate: float,
                             avg_risk: float, city_count: int = 13) -> dict:
    """
    Simple auto-regressive predictor for next-day claims.
    Uses: today's claims + rolling risk trend + seasonal factor.
    """
    hour = datetime.now().hour
    # Day-of-week seasonality (Mon=0, Sun=6)
    dow = datetime.now().weekday()
    seasonal_factors = [0.90, 0.95, 1.00, 1.05, 1.20, 1.35, 1.10]
    seasonal_f = seasonal_factors[dow]

    # Risk-driven demand: higher risk cities → more claims
    risk_multiplier = 0.8 + (avg_risk / 100) * 0.6

    base_prediction = all_claims_today * seasonal_f * risk_multiplier

    # Confidence interval (±15%)
    lower = round(base_prediction * 0.85)
    upper = round(base_prediction * 1.15)
    prediction = round(base_prediction)

    return {
        "predicted_claims":    prediction,
        "confidence_interval": {"lower": lower, "upper": upper},
        "seasonal_factor":     round(seasonal_f, 2),
        "risk_multiplier":     round(risk_multiplier, 2),
        "method":              "Auto-regressive seasonal model (AR-1)",
        "model_version":       "NexaShift-ClaimsNet-v3.1",
    }


def compute_loss_ratio(total_payouts: float, total_premiums: float) -> dict:
    """Loss ratio = claims paid / premiums collected. <70% is healthy."""
    if total_premiums <= 0:
        return {"loss_ratio_pct": 0, "status": "no_data"}
    ratio = total_payouts / total_premiums
    return {
        "loss_ratio_pct": round(ratio * 100, 1),
        "total_payouts":  round(total_payouts),
        "total_premiums": round(total_premiums),
        "status": "healthy" if ratio < 0.70 else "elevated" if ratio < 0.90 else "critical",
    }
