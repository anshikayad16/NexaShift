import time

users         = {}
claims        = {}
policies      = {}
weather_cache = {}
trigger_log   = []
payout_logs   = {}    # txn_id → payout object
autopilot_states = {} # user_id → autopilot config
fraud_events  = []    # live fraud feed events

WEATHER_CACHE_TTL = 300


def get_cached_weather(city):
    entry = weather_cache.get(city)
    if entry and (time.time() - entry["timestamp"]) < WEATHER_CACHE_TTL:
        return entry["data"]
    return None


def set_cached_weather(city, data):
    weather_cache[city] = {"data": data, "timestamp": time.time()}


def log_trigger(trigger):
    trigger_log.append({**trigger, "timestamp": time.time()})
    if len(trigger_log) > 200:
        trigger_log.pop(0)


def get_or_rebuild_user(user_id, request=None):
    """
    Return the user dict from memory, or rebuild a synthetic one from
    query-string / JSON-body params supplied by the frontend.
    This makes all endpoints resilient to server restarts and Vercel
    cold-start / stateless invocations.
    """
    if not user_id:
        return None

    if user_id in users:
        return users[user_id]

    # Try to reconstruct from request params
    if request is None:
        return None

    # Accept params from query string (GET) or JSON body (POST)
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        name      = body.get("name", request.args.get("name", "Worker"))
        city      = body.get("city", request.args.get("city", "Mumbai"))
        income    = int(body.get("income", request.args.get("income", 20000)))
        work_type = body.get("work_type", request.args.get("work_type", "delivery"))
        risk_score = int(body.get("risk_score", request.args.get("risk_score", 55)))
    else:
        name      = request.args.get("name", "Worker")
        city      = request.args.get("city", "Mumbai")
        income    = int(request.args.get("income", 20000))
        work_type = request.args.get("work_type", "delivery")
        risk_score = int(request.args.get("risk_score", 55))

    user = {
        "user_id":    user_id,
        "name":       name,
        "city":       city,
        "income":     income,
        "work_type":  work_type,
        "risk_score": risk_score,
        "premium":    0,
        "coverage":   income * 3,
        "claim_count": 0,
        "weather":    {},
        "aqi":        100,
    }
    users[user_id] = user
    return user
