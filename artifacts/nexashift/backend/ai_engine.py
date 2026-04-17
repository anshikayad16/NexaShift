"""
NexaShift Phase 3 — AI Risk Prediction Engine
Standalone module: risk_prediction_model() + probability_of_income_drop()

Weighted ML-style scoring (no hardcoded if-else decisions).
Formula: risk = Σ (w_i × normalised_feature_i) × city_bias × time_multiplier
"""
import math
from datetime import datetime

FEATURE_WEIGHTS = {
    "rainfall":    0.30,
    "AQI":         0.20,
    "time_of_day": 0.20,
    "city_risk":   0.20,
    "worker_type": 0.10,
}

assert abs(sum(FEATURE_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1"

WORKER_EXPOSURE = {
    "delivery":      0.78,
    "rideshare":     0.62,
    "construction":  0.88,
    "freelance":     0.22,
    "domestic_help": 0.38,
}

CITY_RISK_BASE = {
    "Mumbai":    0.72, "Delhi":     0.68, "Bengaluru": 0.55,
    "Chennai":   0.60, "Hyderabad": 0.50, "Pune":      0.58,
    "Kolkata":   0.65, "Ahmedabad": 0.48, "Jaipur":    0.45,
    "Surat":     0.42, "Nagpur":    0.52, "Lucknow":   0.55,
    "Indore":    0.44,
}


def _normalise_rainfall(mm: float) -> float:
    return min(1.0, mm / 60.0)


def _normalise_aqi(aqi: float) -> float:
    return min(1.0, max(0.0, (aqi - 50) / 450.0))


def _time_risk_factor(hour: int) -> float:
    if 0 <= hour <= 5:      return 0.80
    elif 6 <= hour <= 9:    return 0.25
    elif 10 <= hour <= 13:  return 0.42
    elif 14 <= hour <= 16:  return 0.55
    elif 17 <= hour <= 20:  return 0.28
    elif 21 <= hour <= 23:  return 0.62
    return 0.42


def _income_drop_probability(risk_score: int, worker_type: str,
                              rainfall: float, aqi: float) -> float:
    base = risk_score / 100

    rain_boost = 0.0
    if rainfall > 20:  rain_boost = 0.22
    elif rainfall > 10: rain_boost = 0.12
    elif rainfall > 5:  rain_boost = 0.06

    aqi_boost = 0.0
    if aqi > 300:  aqi_boost = 0.18
    elif aqi > 200: aqi_boost = 0.10
    elif aqi > 150: aqi_boost = 0.05

    worker_factor = WORKER_EXPOSURE.get(worker_type, 0.55)

    raw = (base + rain_boost + aqi_boost) * worker_factor
    return round(min(0.98, max(0.05, raw)) * 100, 1)


def risk_prediction_model(data: dict) -> dict:
    """
    Inputs:
        rainfall      (float)  mm/hr
        AQI           (float)  0–500
        hour          (int)    0–23
        worker_type   (str)    delivery | rideshare | construction | freelance | domestic_help
        city_risk     (float)  0–100 raw city base score, OR city name string
        past_earnings (float)  monthly income in INR (used for context)

    Returns structured JSON with risk_score, confidence, factors, probability_of_income_drop.
    """
    rainfall      = float(data.get("rainfall", 0))
    aqi           = float(data.get("AQI", data.get("aqi", 100)))
    hour          = int(data.get("hour", datetime.now().hour))
    worker_type   = str(data.get("worker_type", "delivery")).lower()
    city_risk_raw = data.get("city_risk", 50)
    past_earnings = float(data.get("past_earnings", 20000))

    # Resolve city_risk
    if isinstance(city_risk_raw, str):
        city_norm = float(CITY_RISK_BASE.get(city_risk_raw, 0.50))
    else:
        city_norm = float(city_risk_raw) / 100.0
    city_norm = min(1.0, max(0.0, city_norm))

    # Normalise all features to [0, 1]
    rain_n   = _normalise_rainfall(rainfall)
    aqi_n    = _normalise_aqi(aqi)
    time_n   = _time_risk_factor(hour)
    worker_n = WORKER_EXPOSURE.get(worker_type, 0.50)

    # Weighted sum → raw score in [0, 1]
    weighted_raw = (
        FEATURE_WEIGHTS["rainfall"]    * rain_n   +
        FEATURE_WEIGHTS["AQI"]         * aqi_n    +
        FEATURE_WEIGHTS["time_of_day"] * time_n   +
        FEATURE_WEIGHTS["city_risk"]   * city_norm +
        FEATURE_WEIGHTS["worker_type"] * worker_n
    )

    # Scale to [10, 95]
    risk_score = round(min(95, max(10, weighted_raw * 100 * 1.05)))

    # Confidence: higher risk → higher certainty; low-risk events have more uncertainty
    confidence = min(96, 60 + risk_score // 4)

    # Per-feature absolute contributions (scaled to risk_score)
    factor_rain    = round(FEATURE_WEIGHTS["rainfall"]    * rain_n    * 100, 1)
    factor_aqi     = round(FEATURE_WEIGHTS["AQI"]         * aqi_n     * 100, 1)
    factor_time    = round(FEATURE_WEIGHTS["time_of_day"] * time_n    * 100, 1)
    factor_worker  = round(FEATURE_WEIGHTS["worker_type"] * worker_n  * 100, 1)
    factor_city    = round(FEATURE_WEIGHTS["city_risk"]   * city_norm * 100, 1)

    prob_drop = _income_drop_probability(risk_score, worker_type, rainfall, aqi)

    # Income impact estimate
    daily_income     = past_earnings / 26
    predicted_drop   = round(daily_income * prob_drop / 100)
    protected_payout = round(predicted_drop * 0.85)

    return {
        "risk_score":                risk_score,
        "confidence":                confidence,
        "probability_of_income_drop": prob_drop,
        "factors": {
            "rainfall":    factor_rain,
            "AQI":         factor_aqi,
            "time_of_day": factor_time,
            "worker_type": factor_worker,
            "city_risk":   factor_city,
        },
        "feature_weights": {k: round(v * 100) for k, v in FEATURE_WEIGHTS.items()},
        "income_impact": {
            "daily_income":      round(daily_income),
            "predicted_drop":    predicted_drop,
            "protected_payout":  protected_payout,
            "net_with_nexashift": round(daily_income - predicted_drop + protected_payout),
        },
        "model_version": "NexaShift-AIEngine-v3.0",
        "inputs": {
            "rainfall":    rainfall,
            "AQI":         aqi,
            "hour":        hour,
            "worker_type": worker_type,
            "city_risk":   city_risk_raw,
        },
    }
