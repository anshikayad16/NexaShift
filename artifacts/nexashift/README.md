# NexaShift — Real-Time AI Earnings OS

**Phase 3: Scale & Optimize** — AI Risk Engine · Fraud Detection · Instant Payout · Admin Intelligence

A production-grade income protection platform for India's 100M+ gig workers. NexaShift uses real-time weather, AQI, and behavioral signals to auto-detect disruptions, score fraud risk, and credit UPI payouts — all in under 2 hours.

---

## Problem Statement

Gig workers face unpredictable income loss due to environmental disruptions — rain, air pollution, heatwaves, platform outages. There is no safety net. NexaShift fixes that.

---

## What's Inside

### Backend (Python Flask — in-memory only, no database)
| Module | Description |
|--------|-------------|
| `backend/app.py` | Flask app, 16 registered blueprints |
| `backend/ai_engine.py` | `risk_prediction_model()` — weighted ML scoring with explainability |
| `backend/income_protection.py` | `generate_protection_plan()` + `/ai/protection-plan` API |
| `backend/services/fraud_engine.py` | 6-signal trust scoring (weather · GPS · frequency · timing · device · amount) |
| `backend/services/ml_engine.py` | Risk, loss, premium, and claims prediction models |
| `backend/services/payout_engine.py` | UPI payout state machine (INITIATED → SUCCESS) |
| `backend/utils/memory_store.py` | In-memory storage — no external DB required |

### Key API Endpoints
| Endpoint | Description |
|----------|-------------|
| `POST /register` | Register worker + activate protection policy |
| `POST /claim/process` | File claim with 6-signal fraud check |
| `GET /ai/protection-plan` | Personalised safe/avoid hours + AI action |
| `GET /insights` | Weekly earnings, risk trend, AI explanation |
| `GET /admin/metrics` | Loss ratio · fraud summary · premium adjustments · city data |
| `GET /admin/stats` | Full admin dashboard data |
| `GET /map-data` | Real-time city risk data (13 cities, Leaflet.js) |
| `GET /ml/predict-risk` | ML risk score with feature contributions |
| `GET /ml/explain-risk` | Full explainability for risk model |
| `GET /autopilot/plan` | AI-generated 24-hour shift schedule |
| `GET /simulate` | Disruption scenario simulation |
| `POST /payout/initiate` | Start UPI payout flow |
| `POST /payout/advance/:txn_id` | Advance payout state machine |

### Frontend (Vanilla HTML/CSS/JS — no frameworks)
- **Dark premium UI** with real-time animations and LIVE badges
- **Leaflet.js map** with city risk + AQI + rainfall markers
- **Disruption Simulator** — 5-step AI pipeline: Detect → Claim → Fraud → Decision → UPI
- **AI Insights tab** — AI explanation banner, 7-day risk trend, protection plan
- **Shift Tracker** — log hourly earnings with AI tips during your shift
- **AI Autopilot** — personalized 24-hour shift schedule
- **Admin Dashboard** — loss ratio, fraud analytics, city risk chart

---

## Local Run

### Step 1 — Install dependencies
```bash
pip install flask flask-cors
```

### Step 2 — Start the backend
```bash
cd artifacts/nexashift
python -m backend.app
```

Open `http://localhost:5000` — Flask serves both the API and the frontend.

---

## Render Deployment (Backend)

1. Connect GitHub repo on [render.com](https://render.com)
2. Create a **Web Service**
3. Configure:
   - **Root directory:** `artifacts/nexashift`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python -m backend.app`
   - **Environment:** Python 3
4. `PORT` is automatically injected by Render — no changes needed

---

## Vercel Deployment (Frontend — Static)

1. Set the API base URL in `frontend/script.js` to your Render backend URL
2. Deploy the `frontend/` folder on [vercel.com](https://vercel.com)
3. `vercel.json` handles SPA routing

> For Replit: the Flask server serves both API + frontend. No separate Vercel step needed.

---

## Architecture

```
User
  │
  ├── Register → /register → policy created, risk scored
  │
  ├── Dashboard → /dashboard/summary → live weather + risk + coverage
  │
  ├── Disruption Detected → /simulate
  │     └── AI Risk Engine → /ml/predict-risk
  │           └── Auto-Claim → /claim/process
  │                 └── Fraud Engine (6 signals)
  │                       └── Decision → UPI Payout → /payout/initiate
  │
  ├── Insights → /insights → earnings + risk trend + AI explanation
  │     └── Protection Plan → /ai/protection-plan
  │
  └── Admin → /admin/metrics → loss ratio + fraud + city data
```

---

## AI Models

| Model | Description |
|-------|-------------|
| `NexaShift-AIEngine-v3.0` | Risk prediction: rainfall × AQI × time × city × worker_type |
| `NexaShift-RiskNet-v3.1` | Weighted feature risk scoring with confidence |
| `NexaShift-FraudNet-v3` | 6-signal fraud detection — no binary rules |
| `NexaShift-LossNet-v3.1` | Income loss + NexaShift payout projection |
| `NexaShift-PremiumNet-v3.1` | Dynamic premium pricing (income × risk × location) |
| `NexaShift-ClaimsNet-v3.1` | Next-day claims volume prediction (AR-1 seasonal) |
| `NexaShift-ProtectionEngine-v3.0` | Safe windows, avoid hours, coverage triggers |

---

## Requirements

```
flask>=3.0
flask-cors>=4.0
requests>=2.31
```

**No database. No external AI API keys. All models run in-process. 100% deployable.**
