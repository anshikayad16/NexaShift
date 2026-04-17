import random
import math
from datetime import datetime
from backend.utils.mock_data import CITY_DATA

WORK_TYPE_RISK = {
    "delivery": 18,
    "rideshare": 12,
    "construction": 22,
    "freelance": -5,
    "domestic_help": 6,
}

INCOME_RISK = [
    (15000, 15),
    (25000, 5),
    (50000, -8),
    (float("inf"), -14),
]


def _income_risk(income: int) -> int:
    for threshold, delta in INCOME_RISK:
        if income < threshold:
            return delta
    return -14


def compute_risk_score(city: str, work_type: str, income: int,
                       weather: dict = None, aqi: int = None) -> int:
    city_info = CITY_DATA.get(city, {})
    base = city_info.get("base_risk", 50)

    base += WORK_TYPE_RISK.get(work_type, 0)
    base += _income_risk(income)

    if weather:
        rainfall = weather.get("rainfall", 0)
        temp = weather.get("temp", 28)
        humidity = weather.get("humidity", 60)

        base += min(25, rainfall * 1.8)
        if temp > 40:
            base += 15
        elif temp > 35:
            base += 8
        base += max(0, (humidity - 70) * 0.3)

    if aqi is not None:
        if aqi > 300:
            base += 20
        elif aqi > 200:
            base += 12
        elif aqi > 150:
            base += 6

    hour = datetime.now().hour
    if 0 <= hour < 6:
        base += 5
    elif 9 <= hour <= 11 or 18 <= hour <= 21:
        base -= 5

    jitter = random.randint(-4, 4)
    return min(max(round(base + jitter), 10), 95)


def compute_weather_risk_factor(weather: dict, aqi: int) -> float:
    factor = 1.0
    rainfall = weather.get("rainfall", 0)
    temp = weather.get("temp", 28)
    if rainfall > 20:
        factor += 0.35
    elif rainfall > 10:
        factor += 0.20
    elif rainfall > 5:
        factor += 0.10

    if temp > 42:
        factor += 0.25
    elif temp > 38:
        factor += 0.12

    if aqi > 300:
        factor += 0.30
    elif aqi > 200:
        factor += 0.15

    return round(min(factor, 2.2), 2)
