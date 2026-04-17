# NexaShift — Real-Time AI Earnings OS for Gig Workers

## Overview

NexaShift is a real-time AI decision engine that predicts, recommends, and auto-protects gig worker income. Built with Python Flask (backend) and plain HTML/CSS/JavaScript (frontend). Core flow: **Predict → Decide → Act → Protect → Explain**.

## Stack

- **Backend**: Python Flask with Flask-CORS, requests
- **Frontend**: Vanilla HTML, CSS, JavaScript (fetch API only — no frameworks)
- **Storage**: In-memory Python dictionaries (`utils/memory_store.py`)
- **Runtime**: Python 3.11

## Project Structure

```
artifacts/nexashift/
├── backend/
│   ├── app.py                    # Flask app entry point + blueprint registration
│   ├── routes/
│   │   ├── auth.py               # POST /register, GET /users
│   │   ├── policy.py             # GET /policy/<id>, POST /policy/create
│   │   ├── claim.py              # POST /claim/process, GET /claims/<id>
│   │   ├── trigger.py            # GET /triggers — dynamic, weather-driven
│   │   ├── map.py                # GET /map-data — live weather per city
│   │   ├── decision.py           # GET /daily-plan/<id>, GET /dashboard/summary,
│   │   │                         # GET /live-decision/<id>, GET /ai/explain
│   │   ├── simulation.py         # GET /simulate — live-conditions adjusted
│   │   └── external.py           # GET /real-weather/<city>, GET /aqi/<city>,
│   │                             # POST /location-update
│   ├── services/
│   │   ├── risk_engine.py        # ML-like risk score (weather + AQI + time + work type)
│   │   ├── pricing_engine.py     # Dynamic premium: (income × risk × 0.55 × 7) × weather_factor
│   │   ├── decision_engine.py    # Daily plan with live weather conditions
│   │   ├── simulation_engine.py  # What-if simulation adjusted for live conditions
│   │   ├── fraud_engine.py       # Fraud risk assessment for claims
│   │   ├── explain_engine.py     # AI explainability — factors, confidence, data lineage
│   │   └── trust_engine.py       # Trust scoring
│   └── utils/
│       ├── memory_store.py       # Central in-memory store for users, claims, weather cache
│       └── mock_data.py          # City base data, scenario definitions
├── frontend/
│   ├── index.html                # Main SPA
│   ├── style.css                 # Full dark theme, live mode UI, weather strip
│   └── script.js                 # All JS: live mode, geolocation, real-time polling
└── requirements.txt              # flask, flask-cors, requests
```

## Key Real-Time Features

### Live Mode (Core Differentiator)
- Toggle in dashboard: `LIVE MODE ON`
- Calls `/live-decision/<user_id>` every 10 seconds
- Shows GO / CAUTION / STOP recommendation with expected earnings
- Auto-trigger detection: fires income protection payout automatically when rain > 10mm/hr or AQI > 250

### Weather Integration
- `/real-weather/<city>` — fetches from OpenWeatherMap if `OPENWEATHERMAP_API_KEY` env var is set, otherwise simulates city-specific patterns
- Weather cache TTL: 5 minutes
- Drives risk score, premium, triggers, and live decisions

### ML-Like Risk Engine
- Combines: city base risk + work type exposure + income bracket + live weather rainfall + temperature + AQI + time of day
- Outputs score 0–100

### Explainability Engine
- Every decision includes: factors with weights, data used, confidence %, plain-English summary
- Example: "Rainfall 18.7mm/hr → 59% income drop → auto-payout ₹3,500 triggered"

### Geolocation
- "Use My Location" button in dashboard
- Finds nearest city, fetches live weather for that location

### Zero-Touch Claims
- Claim amount auto-adjusted based on live rainfall/AQI at claim time
- Triggers auto-detected: no manual filing needed when weather threshold crossed

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /register | Worker registration with live weather risk |
| GET | /live-decision/<id> | GO/STOP recommendation (10s polling) |
| GET | /dashboard/summary | Stats with live risk score |
| GET | /daily-plan/<id> | AI daily schedule with weather |
| GET | /triggers | Dynamic triggers from live weather |
| GET | /map-data | City risk + live weather data |
| GET | /simulate | What-if scenario (live-adjusted) |
| GET | /ai/explain | Explainability for any event |
| GET | /real-weather/<city> | Live weather (OWM or simulated) |
| GET | /aqi/<city> | AQI level |
| POST | /location-update | Geolocation → nearest city |
| POST | /claim/process | AI fraud check + auto-approval |

## Deployment

- **Backend (Render)**: Set `OPENWEATHERMAP_API_KEY` env var for real weather. Runs on `0.0.0.0:$PORT`.
- **Frontend (Vercel)**: Pure static files. Update `API_URL` constant in `script.js` if deploying separately.
- No database required — in-memory state only.
