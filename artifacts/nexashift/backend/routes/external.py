import os
import math
import random
import time
from datetime import datetime
from flask import Blueprint, request, jsonify

try:
    import requests as req_lib
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from backend.utils.memory_store import get_cached_weather, set_cached_weather
from backend.utils.mock_data import CITY_DATA

external_bp = Blueprint("external", __name__)

OWM_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "")

CITY_COORDS = {
    city: (info["lat"], info["lng"])
    for city, info in CITY_DATA.items()
}

def _simulated_weather(city: str) -> dict:
    hour = datetime.now().hour
    info = CITY_DATA.get(city, {})
    weather_tag = info.get("weather", "Clear")

    rainfall = 0.0
    if weather_tag == "Rain":
        rainfall = round(random.uniform(8, 35), 1)
    elif weather_tag in ("Humid", "Hazy"):
        rainfall = round(random.uniform(0, 8), 1)
    elif hour in (15, 16, 17) and random.random() < 0.25:
        rainfall = round(random.uniform(2, 12), 1)

    base_temp = {"Mumbai": 30, "Delhi": 34, "Bengaluru": 26, "Chennai": 32,
                 "Hyderabad": 33, "Pune": 28, "Kolkata": 31, "Ahmedabad": 36,
                 "Jaipur": 38, "Surat": 32}.get(city, 30)
    temp = round(base_temp + random.uniform(-2, 3), 1)
    if 11 <= hour <= 15:
        temp += 3

    humidity = round(random.uniform(55, 90), 0)
    if weather_tag == "Rain":
        humidity = round(random.uniform(78, 95), 0)
    elif weather_tag == "Hot":
        humidity = round(random.uniform(25, 50), 0)

    return {
        "city": city,
        "source": "simulated",
        "rainfall": rainfall,
        "temp": temp,
        "humidity": int(humidity),
        "description": weather_tag,
        "wind_speed": round(random.uniform(5, 25), 1),
    }


def _real_weather(city: str) -> dict:
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={OWM_KEY}&units=metric"
        r = req_lib.get(url, timeout=5)
        if r.status_code == 200:
            d = r.json()
            rain_data = d.get("rain", {})
            return {
                "city": city,
                "source": "openweathermap",
                "rainfall": rain_data.get("1h", 0.0),
                "temp": d["main"]["temp"],
                "humidity": d["main"]["humidity"],
                "description": d["weather"][0]["description"].title(),
                "wind_speed": d["wind"]["speed"],
            }
    except Exception:
        pass
    return None


def get_weather(city: str) -> dict:
    cached = get_cached_weather(city)
    if cached:
        return cached
    data = None
    if OWM_KEY and REQUESTS_AVAILABLE:
        data = _real_weather(city)
    if not data:
        data = _simulated_weather(city)
    set_cached_weather(city, data)
    return data


def get_aqi(city: str) -> int:
    hour = datetime.now().hour
    info = CITY_DATA.get(city, {})
    weather_tag = info.get("weather", "Clear")
    base_aqi = {
        "Delhi": 280, "Jaipur": 220, "Ahmedabad": 190,
        "Mumbai": 150, "Kolkata": 170, "Chennai": 120,
        "Pune": 130, "Bengaluru": 100, "Hyderabad": 110, "Surat": 140,
    }.get(city, 130)

    if weather_tag in ("Rain",):
        base_aqi = max(50, base_aqi - 60)
    if 7 <= hour <= 10 or 18 <= hour <= 22:
        base_aqi += 30

    return min(500, base_aqi + random.randint(-20, 20))


@external_bp.route("/real-weather/<city>", methods=["GET"])
def real_weather(city):
    city = city.strip().title()
    data = get_weather(city)
    return jsonify(data)


@external_bp.route("/aqi/<city>", methods=["GET"])
def aqi_route(city):
    city = city.strip().title()
    aqi = get_aqi(city)
    level = "Good" if aqi < 51 else "Moderate" if aqi < 101 else "Unhealthy for Sensitive" if aqi < 151 else "Unhealthy" if aqi < 201 else "Very Unhealthy" if aqi < 301 else "Hazardous"
    return jsonify({"city": city, "aqi": aqi, "level": level})


@external_bp.route("/location-update", methods=["POST"])
def location_update():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    lat = data.get("lat")
    lng = data.get("lng")
    if not user_id or lat is None or lng is None:
        return jsonify({"error": "user_id, lat and lng required"}), 400

    from backend.utils.memory_store import users
    user = users.get(user_id)
    if user:
        user["lat"] = lat
        user["lng"] = lng

    nearest_city = _nearest_city(lat, lng)
    weather = get_weather(nearest_city)
    aqi = get_aqi(nearest_city)

    return jsonify({
        "nearest_city": nearest_city,
        "weather": weather,
        "aqi": aqi,
        "message": f"Location locked to {nearest_city}",
    })


def _nearest_city(lat: float, lng: float) -> str:
    best = "Mumbai"
    best_dist = float("inf")
    for city, (clat, clng) in CITY_COORDS.items():
        dist = math.sqrt((lat - clat) ** 2 + (lng - clng) ** 2)
        if dist < best_dist:
            best_dist = dist
            best = city
    return best
