CITY_DATA = {
    "Mumbai":    {"lat": 19.076, "lng": 72.877, "base_risk": 72, "demand": 95, "avg_payout": 3200, "weather": "Rain"},
    "Delhi":     {"lat": 28.704, "lng": 77.102, "base_risk": 68, "demand": 92, "avg_payout": 2800, "weather": "Hazy"},
    "Bengaluru": {"lat": 12.971, "lng": 77.594, "base_risk": 55, "demand": 88, "avg_payout": 2600, "weather": "Cloudy"},
    "Chennai":   {"lat": 13.083, "lng": 80.270, "base_risk": 60, "demand": 80, "avg_payout": 2400, "weather": "Humid"},
    "Hyderabad": {"lat": 17.385, "lng": 78.487, "base_risk": 50, "demand": 78, "avg_payout": 2200, "weather": "Clear"},
    "Pune":      {"lat": 18.520, "lng": 73.856, "base_risk": 58, "demand": 75, "avg_payout": 2100, "weather": "Windy"},
    "Kolkata":   {"lat": 22.572, "lng": 88.363, "base_risk": 65, "demand": 70, "avg_payout": 2000, "weather": "Humid"},
    "Ahmedabad": {"lat": 23.022, "lng": 72.571, "base_risk": 48, "demand": 68, "avg_payout": 1900, "weather": "Hot"},
    "Jaipur":    {"lat": 26.912, "lng": 75.787, "base_risk": 45, "demand": 62, "avg_payout": 1800, "weather": "Hot"},
    "Surat":     {"lat": 21.170, "lng": 72.831, "base_risk": 42, "demand": 60, "avg_payout": 1700, "weather": "Clear"},
    "Nagpur":    {"lat": 21.145, "lng": 79.088, "base_risk": 52, "demand": 65, "avg_payout": 1950, "weather": "Hot"},
    "Lucknow":   {"lat": 26.847, "lng": 80.947, "base_risk": 55, "demand": 66, "avg_payout": 1850, "weather": "Hazy"},
    "Indore":    {"lat": 22.719, "lng": 75.857, "base_risk": 44, "demand": 63, "avg_payout": 1750, "weather": "Clear"},
}

# ── Hyper-local micro-zones inside each city ──────────────────
# demand 0–100, risk_offset relative to city base, zone_type for color coding
MICRO_ZONES = {
    "Mumbai": [
        {"zone": "Andheri West",    "lat": 19.1334, "lng": 72.8286, "demand": 95, "risk_offset":  5, "type": "commercial",   "peak_hours": "7–10 AM, 5–9 PM"},
        {"zone": "Bandra-Kurla",    "lat": 19.0596, "lng": 72.8660, "demand": 88, "risk_offset": -3, "type": "corporate",    "peak_hours": "8–11 AM, 6–8 PM"},
        {"zone": "Powai",           "lat": 19.1197, "lng": 72.9050, "demand": 82, "risk_offset": -6, "type": "residential",  "peak_hours": "7–9 AM, 7–9 PM"},
        {"zone": "Dadar",           "lat": 19.0176, "lng": 72.8450, "demand": 92, "risk_offset":  8, "type": "transit_hub",  "peak_hours": "7 AM–10 AM, All PM"},
        {"zone": "Thane",           "lat": 19.1978, "lng": 72.9783, "demand": 78, "risk_offset":  4, "type": "suburb",       "peak_hours": "8–10 AM, 6–8 PM"},
    ],
    "Delhi": [
        {"zone": "Connaught Place", "lat": 28.6329, "lng": 77.2195, "demand": 96, "risk_offset":  2, "type": "commercial",   "peak_hours": "9 AM–9 PM"},
        {"zone": "Dwarka",          "lat": 28.5921, "lng": 77.0460, "demand": 80, "risk_offset": -4, "type": "residential",  "peak_hours": "7–9 AM, 5–8 PM"},
        {"zone": "Saket",           "lat": 28.5244, "lng": 77.2066, "demand": 85, "risk_offset": -2, "type": "commercial",   "peak_hours": "10 AM–9 PM"},
        {"zone": "Lajpat Nagar",    "lat": 28.5677, "lng": 77.2433, "demand": 91, "risk_offset":  6, "type": "market",       "peak_hours": "10 AM–8 PM"},
        {"zone": "Gurugram",        "lat": 28.4595, "lng": 77.0266, "demand": 88, "risk_offset": -5, "type": "corporate",    "peak_hours": "8–10 AM, 5–8 PM"},
    ],
    "Bengaluru": [
        {"zone": "Koramangala",     "lat": 12.9352, "lng": 77.6245, "demand": 94, "risk_offset":  3, "type": "commercial",   "peak_hours": "8 AM–10 PM"},
        {"zone": "Whitefield",      "lat": 12.9698, "lng": 77.7499, "demand": 89, "risk_offset": -2, "type": "corporate",    "peak_hours": "8–10 AM, 5–8 PM"},
        {"zone": "Indiranagar",     "lat": 12.9784, "lng": 77.6408, "demand": 91, "risk_offset":  1, "type": "nightlife",    "peak_hours": "7–10 PM"},
        {"zone": "HSR Layout",      "lat": 12.9116, "lng": 77.6389, "demand": 86, "risk_offset": -4, "type": "residential",  "peak_hours": "7–9 AM, 6–9 PM"},
        {"zone": "Electronic City", "lat": 12.8458, "lng": 77.6603, "demand": 78, "risk_offset": -7, "type": "corporate",    "peak_hours": "8–10 AM, 5–7 PM"},
    ],
    "Chennai": [
        {"zone": "T. Nagar",        "lat": 13.0358, "lng": 80.2339, "demand": 90, "risk_offset":  5, "type": "market",       "peak_hours": "10 AM–8 PM"},
        {"zone": "Anna Nagar",      "lat": 13.0850, "lng": 80.2101, "demand": 84, "risk_offset": -2, "type": "residential",  "peak_hours": "7–9 AM, 6–9 PM"},
        {"zone": "Velachery",       "lat": 12.9815, "lng": 80.2180, "demand": 82, "risk_offset": -4, "type": "commercial",   "peak_hours": "8–10 AM, 5–8 PM"},
        {"zone": "Adyar",           "lat": 13.0012, "lng": 80.2565, "demand": 80, "risk_offset": -6, "type": "residential",  "peak_hours": "7–9 AM, 5–8 PM"},
        {"zone": "Tambaram",        "lat": 12.9249, "lng": 80.1000, "demand": 74, "risk_offset":  3, "type": "suburb",       "peak_hours": "7–9 AM, 5–7 PM"},
    ],
    "Hyderabad": [
        {"zone": "Banjara Hills",   "lat": 17.4126, "lng": 78.4480, "demand": 90, "risk_offset": -5, "type": "commercial",   "peak_hours": "9 AM–9 PM"},
        {"zone": "HITEC City",      "lat": 17.4400, "lng": 78.3489, "demand": 92, "risk_offset": -8, "type": "corporate",    "peak_hours": "8–10 AM, 5–8 PM"},
        {"zone": "Gachibowli",      "lat": 17.4400, "lng": 78.3498, "demand": 87, "risk_offset": -6, "type": "corporate",    "peak_hours": "8–10 AM, 6–9 PM"},
        {"zone": "Secunderabad",    "lat": 17.4399, "lng": 78.4983, "demand": 82, "risk_offset":  2, "type": "transit_hub",  "peak_hours": "7 AM–9 PM"},
        {"zone": "Madhapur",        "lat": 17.4487, "lng": 78.3903, "demand": 88, "risk_offset": -4, "type": "nightlife",    "peak_hours": "7–10 PM"},
    ],
    "Pune": [
        {"zone": "Hinjewadi",       "lat": 18.5912, "lng": 73.7381, "demand": 85, "risk_offset": -4, "type": "corporate",    "peak_hours": "8–10 AM, 5–8 PM"},
        {"zone": "Kothrud",         "lat": 18.5074, "lng": 73.8077, "demand": 80, "risk_offset": -2, "type": "residential",  "peak_hours": "7–9 AM, 6–9 PM"},
        {"zone": "Viman Nagar",     "lat": 18.5679, "lng": 73.9143, "demand": 82, "risk_offset": -3, "type": "commercial",   "peak_hours": "8–10 AM, 5–8 PM"},
        {"zone": "Kharadi",         "lat": 18.5515, "lng": 73.9354, "demand": 78, "risk_offset": -5, "type": "corporate",    "peak_hours": "8–10 AM, 5–7 PM"},
        {"zone": "Hadapsar",        "lat": 18.5089, "lng": 73.9260, "demand": 76, "risk_offset":  3, "type": "industrial",   "peak_hours": "7–9 AM, 4–7 PM"},
    ],
}

WORK_TYPES = ["delivery", "rideshare", "construction", "freelance", "domestic_help"]

SCENARIOS = {
    "rain": {
        "label": "Heavy Rain",
        "impact": 0.40,
        "description": "Heavy rainfall warning. Expected to reduce delivery income by 35–45%.",
        "recommendation": "Switch to Instamart grocery deliveries — demand spikes 3x during rain.",
        "payout": 3500,
    },
    "aqi": {
        "label": "High AQI (Air Quality)",
        "impact": 0.25,
        "description": "Air quality index >300. Outdoor work impact expected.",
        "recommendation": "Wear N95 mask. Opt for AC cab services — surge pricing active.",
        "payout": 2500,
    },
    "heat": {
        "label": "Extreme Heat (45°C+)",
        "impact": 0.30,
        "description": "Heat wave advisory. Outdoor delivery workers at risk.",
        "recommendation": "Shift hours to 6–9 AM and 7–10 PM. Avoid 11 AM–4 PM.",
        "payout": 2800,
    },
    "platform_outage": {
        "label": "Platform App Outage",
        "impact": 0.60,
        "description": "Primary platform down. Zero orders for estimated 4–6 hours.",
        "recommendation": "Switch to backup platforms (Porter, Dunzo). File platform outage claim.",
        "payout": 4500,
    },
    "upi_down": {
        "label": "UPI Payment Down",
        "impact": 0.35,
        "description": "UPI services disrupted. Cash collections only.",
        "recommendation": "Accept only pre-paid orders. Enable COD wallets as backup.",
        "payout": 3000,
    },
    "festival": {
        "label": "Festival Surge",
        "impact": -0.50,
        "description": "Festival demand surge! Earnings expected to spike.",
        "recommendation": "Maximize hours. Work 12+ hour shifts for 2–3x normal income.",
        "payout": 0,
    },
    "accident": {
        "label": "Road Accident / Injury",
        "impact": 1.00,
        "description": "Total income loss during recovery period.",
        "recommendation": "File emergency claim immediately. Medical + income protection activated.",
        "payout": 8000,
    },
}
