# Deploying NexaShift to Vercel

This guide deploys the full NexaShift app (Flask backend + HTML frontend) to Vercel using the Python serverless runtime. Follow every step exactly.

---

## Prerequisites

- A [Vercel account](https://vercel.com) (free tier works)
- Your project pushed to a GitHub repository
- Node.js installed locally (for the Vercel CLI, optional)

---

## Step 1 — Push to GitHub

Make sure your project is in a GitHub repo. The root of the repo should contain the `artifacts/nexashift/` folder **or** you can set the Vercel root directory (see Step 3).

---

## Step 2 — Import to Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **"Import Git Repository"**
3. Select your GitHub repo

---

## Step 3 — Configure Root Directory

In the **"Configure Project"** screen:

| Setting | Value |
|---|---|
| **Root Directory** | `artifacts/nexashift` |
| **Framework Preset** | Other |
| **Build Command** | *(leave blank)* |
| **Output Directory** | *(leave blank)* |
| **Install Command** | `pip install -r requirements.txt` |

> The `vercel.json` file in the root handles all routing automatically.

---

## Step 4 — Environment Variables (Optional)

If you have an OpenWeatherMap API key for live weather data, add it:

| Key | Value |
|---|---|
| `WEATHER_API_KEY` | `your_openweathermap_key` |

> Without this key the app falls back to simulated weather data — it still works fully.

---

## Step 5 — Deploy

Click **"Deploy"**. Vercel will:
1. Detect Python from `requirements.txt`
2. Install `flask`, `flask-cors`, `requests`
3. Bundle `api/index.py` as a serverless function
4. Route all requests through the Flask app

---

## Step 6 — Verify

After deployment, visit your `.vercel.app` URL. You should see the NexaShift registration screen.

**If the page loads but API calls fail**, check:
- The **Function Logs** tab in Vercel dashboard for Python errors
- That `requirements.txt` lists `flask`, `flask-cors`, `requests`

---

## Project Structure (What Vercel Sees)

```
artifacts/nexashift/
├── api/
│   └── index.py          ← Vercel Python entry point
├── backend/
│   ├── app.py            ← Flask app
│   ├── routes/
│   ├── services/
│   └── utils/
├── frontend/
│   ├── index.html        ← Served by Flask
│   ├── style.css
│   └── script.js
├── requirements.txt      ← Python dependencies
└── vercel.json           ← Routing config
```

---

## Important Notes

### In-Memory Storage
The backend uses in-memory storage. On Vercel's serverless runtime, each function call may run in a new instance, so data (user profiles, claims) resets between calls. This is expected behaviour for a demo/prototype.

**For production:** replace the in-memory store with a real database (PostgreSQL, MongoDB, etc.).

### No Localhost
The frontend uses relative API URLs (`/register`, `/map-data`, etc.) so no changes are needed — they automatically resolve to your Vercel domain.

### Weather API
Without a `WEATHER_API_KEY`, the app uses realistic simulated weather. Add the key as an environment variable in the Vercel dashboard for live data.

---

## Local Development

```bash
cd artifacts/nexashift
pip install -r requirements.txt
python -m backend.app
```

Visit `http://localhost:5000`

---

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError: backend` | Make sure Root Directory is set to `artifacts/nexashift` in Vercel |
| `500 Internal Server Error` | Check Vercel Function Logs for the Python traceback |
| Blank page, no styles | CSS/JS are served by Flask — check the Function Logs |
| `requirements.txt not found` | Root Directory must be `artifacts/nexashift`, not the repo root |
