from datetime import datetime
from backend.utils.mock_data import CITY_DATA


def get_daily_plan(user: dict) -> dict:
    city = user.get("city", "Mumbai")
    work_type = user.get("work_type", "delivery")
    income = user.get("income", 20000)
    risk_score = user.get("risk_score", 60)

    city_info = CITY_DATA.get(city, {})
    demand = city_info.get("demand", 70)

    weather_data = user.get("weather", {})
    aqi = user.get("aqi", 100)
    rainfall = weather_data.get("rainfall", 0)
    temp = weather_data.get("temp", 28)
    weather_desc = weather_data.get("description", city_info.get("weather", "Clear"))

    best_hours = []
    avoid_hours = []
    recommendation = ""
    expected_earnings = 0

    if work_type in ("delivery", "rideshare"):
        best_hours = ["7:00 AM – 10:00 AM", "12:00 PM – 2:00 PM", "7:00 PM – 10:00 PM"]
        avoid_hours = ["2:00 PM – 5:00 PM"]
        if rainfall > 15:
            avoid_hours = ["All outdoor periods — heavy rain active"]
            best_hours = ["Indoor grocery zones only"]
            recommendation = (
                f"Heavy rain ({rainfall}mm/hr) in {city}. Switch to Instamart/grocery — "
                "demand spikes 3x during rain. File rain claim for income protection."
            )
        elif rainfall > 5:
            recommendation = (
                f"Light rain in {city}. Focus on indoor pickup zones. "
                "Surge pricing active — accept high-value orders only."
            )
        else:
            recommendation = (
                f"Peak demand in {city} is morning and evening. "
                "Focus on high-density zones. Enable surge notifications."
            )
        daily_rate = income / 26
        factor = 1.0
        if rainfall > 15:
            factor = 0.55
        elif rainfall > 5:
            factor = 0.78
        if aqi > 250:
            factor *= 0.85
        expected_earnings = round(daily_rate * factor * (1 + (demand - 70) / 100))

    elif work_type == "construction":
        best_hours = ["6:00 AM – 11:00 AM", "3:00 PM – 6:00 PM"]
        avoid_hours = ["11:00 AM – 3:00 PM (heat hours)"]
        if temp > 42:
            avoid_hours = ["11:00 AM – 5:00 PM (extreme heat)"]
            recommendation = f"Extreme heat {temp}°C. Stop outdoor work during peak hours. Claim heat-halt allowance."
        elif rainfall > 10:
            recommendation = "Rain halt advisory. Do not work on scaffolding or elevated surfaces. File weather claim."
        else:
            recommendation = "Outdoor work conditions acceptable. Hydration breaks every 90 min. Check air quality."
        expected_earnings = round(income / 26 * (0.8 if temp > 38 else 1.0))

    elif work_type == "freelance":
        best_hours = ["9:00 AM – 1:00 PM", "6:00 PM – 10:00 PM"]
        avoid_hours = ["2:00 PM – 5:00 PM (low response rates)"]
        recommendation = "Send proposals in morning. Follow up in evenings. Leverage festival season for premium rates."
        expected_earnings = round(income / 22)

    else:
        best_hours = ["8:00 AM – 12:00 PM", "4:00 PM – 8:00 PM"]
        avoid_hours = ["12:00 PM – 4:00 PM"]
        recommendation = "Standard shift hours recommended. Check for additional gig opportunities nearby."
        expected_earnings = round(income / 26)

    risk_windows = []
    if rainfall > 10:
        risk_windows.append({"time": "Now", "event": f"Heavy rain {rainfall}mm/hr", "severity": "high"})
    if temp > 40:
        risk_windows.append({"time": "12:00 PM – 4:00 PM", "event": f"Extreme heat {temp}°C", "severity": "high"})
    if aqi > 200:
        risk_windows.append({"time": "Morning/Evening rush", "event": f"AQI {aqi} – health risk", "severity": "medium"})
    if risk_score > 70:
        risk_windows.append({"time": "Peak hours", "event": "High combined risk zone", "severity": "medium"})

    return {
        "city": city,
        "work_type": work_type,
        "weather": f"{weather_desc}, {temp}°C, Rain: {rainfall}mm/hr",
        "best_hours": best_hours,
        "avoid_hours": avoid_hours,
        "recommendation": recommendation,
        "expected_earnings": expected_earnings,
        "risk_windows": risk_windows,
        "demand_score": demand,
        "aqi": aqi,
        "rainfall": rainfall,
    }
