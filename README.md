# NexaShift
**AI Income Protection OS for Gig Workers**

> *"NexaShift is not just an insurance platform, it is a real-time financial safety system for gig workers."*

---

## 📌 Pitch Deck

[View Pitch Deck](your-drive-link-here)

---

## Problem

Gig workers face unpredictable income loss due to heavy rainfall, AQI spikes, heatwaves, platform outages, and accidents. There is no real-time protection system claims are manual, delayed, and unreliable.

**Core Flow:** `Predict → Protect → Detect → Approve → Pay`

---

## Solution

NexaShift is an AI-driven earnings protection OS that predicts income loss using real-time environmental and behavioral data, automatically triggers insurance coverage, detects fraud using multi-signal validation, and instantly processes payouts without manual claims.

---

## Persona & Workflow

**Rahul, Delivery Partner, Chennai** earns ₹700–₹900/day. Income drops 30–50% during rain or high AQI days with no way to anticipate or recover the loss.

| Step | Action |
|------|--------|
| 1. Register | Worker profile created with earnings baseline and city |
| 2. Risk Signal | Live weather + AQI assessed in real time |
| 3. Protection Mode | AI predicts risky windows, suggests safer hours, auto-enables coverage |
| 4. Disruption | Threshold breached → claim auto-triggered, no action needed |
| 5. Fraud Check | Multi-signal Trust Score computed |
| 6. Payout | Amount credited via UPI simulation in real time |

---

## Core Features

| Feature | Description |
|---------|-------------|
| AI Risk Prediction Engine | Risk Score (0–100) with explainable factor breakdown |
| Multi-Signal Fraud Detection | Trust Score using GPS anomaly, weather validation, claim frequency, behavioral deviation |
| Income Protection Mode | Proactive: predicts risk windows, suggests work-type switching, auto-enables coverage |
| Zero-Touch Claims System | Disruption → Risk → Claim → Fraud Check → Approval → Payout, fully automated |
| Instant Payout Simulation | UPI-style payout flow with wallet, transaction history, and receipt UI |
| Intelligence Map | Leaflet.js map of Indian cities with live risk score, AQI, and rainfall data |
| Disruption Simulator | Simulate rain, AQI, heatwave, outage triggers full AI pipeline |
| Behavioral Insights | Weekly earnings trends, risk exposure analytics, personalized recommendations |
| Daily Shift Tracker | Start/stop tracking, hourly earnings logging, daily target progress |
| Admin Dashboard | Loss ratio monitoring, dynamic premium adjustment, fraud summary, city risk analytics |

---

## Premium Model

$$P = \left( E_{\text{base}} \times p_{\text{disruption}} \times r_{\text{loss}} \times 7 \right) \times \lambda$$

| Factor | Example Value |
|--------|---------------|
| Daily Earnings Baseline $E_{\text{base}}$ | ₹800 (4-week rolling avg) |
| Disruption Probability $p_{\text{disruption}}$ | 35% (live weather forecast) |
| Avg Loss Ratio $r_{\text{loss}}$ | 55% |
| Risk Multiplier $\lambda$ | 0.85 (consistent earner, moderate-risk zone) |
| **Weekly Premium** | **≈ ₹39 → up to ₹1,200 coverage** |

---

## Parametric Triggers

Claims fire automatically when thresholds are crossed, no manual filing needed.

| Category | Trigger | Threshold | Source |
|----------|---------|-----------|--------|
| Weather | Rainfall | > 20 mm/hr | OpenWeatherMap, IMD |
| Weather | Extreme Heat | > 42°C for 3+ hrs | IMD |
| Environmental | AQI | > 300 (Hazardous) | AQI API, CPCB |
| Social | Bandh / Curfew | Official order issued | Govt notification |
| Technical | Platform Outage | > 45 min downtime | Uptime monitoring |

---

## Adversarial Defense & Anti-Spoofing Strategy

### 1. Genuine Worker vs. Spoofer

GPS alone is not trusted. The Trust Engine cross-examines five signals:

| Signal | Spoof Red Flag |
|--------|---------------|
| GPS movement (Haversine) | Unnaturally static coordinates; zero drift |
| Accelerometer / gyroscope | Near-zero variance no micro-movements |
| Cell tower data | Tower ID mismatches claimed GPS location |
| Platform app activity | No Swiggy/Zomato activity during disruption window |
| Battery & screen state | Screen off, drain inconsistent with active outdoor use |

Two or more signals tripped → automatic escalation.

### 2. Detecting a Coordinated Fraud Ring

| Data Point | What It Reveals |
|------------|-----------------|
| Claim timing | Simultaneous filings from same zone; genuine disruptions produce staggered claims |
| Device fingerprinting | Same hardware ID across multiple accounts |
| UPI destination | Multiple accounts routing to the same bank account or VPA |
| Referral graph | Tightly clustered rings with disproportionately high claim rates |
| Coverage timing | Minimal earnings history + coverage activated right before a forecast event |

### 3. Flagged Claims Without Penalising Honest Workers

```
Score < 0.4   →  Auto-approve  →  Instant payout
Score 0.4–0.7 →  Soft flag     →  2-hour passive re-verification, then auto-release
Score > 0.7   →  Hard flag     →  Manual review within 24 hrs, worker notified
```

Soft flag: no action from the worker signals re-checked quietly and auto-released if genuine. Hard flag: worker notified transparently with optional screenshot submission. If cleared, ₹25 trust top-up added to the payout.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | HTML5, CSS3 (Dark UI), Vanilla JavaScript |
| Backend | Python Flask, Flask-CORS |
| Maps | Leaflet.js |
| AI Logic | Weighted scoring models, multi-signal decision systems, explainability layers |
| Storage | In-memory (Python dictionaries) |
| APIs | OpenWeatherMap (Weather + AQI) |

---

## Project Structure

```
backend/
  app.py
  ai_engine.py
  fraud_engine.py
  payout.py
  income_protection.py

frontend/
  index.html
  dashboard.html
  map.html
  claims.html
  insights.html
```

---

## How to Run Locally

```bash
# 1. Clone the repository
git clone <your-repo-link>
cd nexashift

# 2. Install dependencies
pip install flask flask-cors

# 3. Run backend
python backend/app.py

# 4. Open in browser
http://localhost:5000
```

---

## Deployment

**Backend (Render)**
- Root Directory: `/backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python app.py`
- Environment Variable: `WEATHER_API_KEY=your_key`

**Frontend (Vercel)**
- Upload `/frontend` folder as static site
- Update API base URL in JS: `const API_URL = "https://your-render-url"`

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register` | POST | Create worker profile |
| `/dashboard/summary` | GET | Dashboard data |
| `/ai/risk` | GET | Risk prediction |
| `/ai/protection-plan` | GET | Income protection plan |
| `/claim/process` | POST | Process claim |
| `/fraud/check` | POST | Fraud evaluation |
| `/payout` | POST | Simulate payout |
| `/map-data` | GET | City risk data |
| `/insights` | GET | Behavioral insights |
| `/admin/metrics` | GET | Admin dashboard |

---

## Demo Flow (For Judges)

1. Register a worker
2. Open dashboard → view AI risk score
3. Enable live mode
4. Trigger a disruption (rain)
5. Watch auto claim generation, fraud analysis, trust score, and instant payout
6. Switch to Admin Dashboard → view loss ratio, premium adjustment, fraud summary

---

## Development Plan

| Phase | Timeline | Deliverables |
|-------|----------|--------------|
| MVP | Weeks 1–4 | Risk engine, decision engine, zero-touch claims, intelligence map, shift tracker |
| AI Models | Weeks 5–8 | Real XGBoost + LSTM models trained on gig worker data |
| Mobile | Weeks 9–12 | React Native app, push alerts, GPS verification |
| Scale | Weeks 13–16 | Swiggy/Zomato API integration, blockchain claim verification, community risk pooling |

---

## Business Impact

- Supports millions of gig workers across India
- Reduces manual claim processing by ~80%
- Enables real-time parametric insurance at scale
- Scalable across cities and platforms

---

Built for DevTrails Hackathon. Focused on real-world impact, AI-driven decisions, and scalable design.
