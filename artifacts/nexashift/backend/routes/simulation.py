from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users
from backend.services.simulation_engine import run_simulation

simulation_bp = Blueprint("simulation", __name__)


@simulation_bp.route("/simulate", methods=["GET"])
def simulate():
    scenario = request.args.get("scenario", "rain")
    user_id = request.args.get("user_id", "")
    user = users.get(user_id, {})
    income_param = request.args.get("income", "")
    try:
        base_income = int(income_param) if income_param and income_param != "undefined" else int(user.get("income", 20000))
    except (ValueError, TypeError):
        base_income = int(user.get("income", 20000))

    city = user.get("city", "Mumbai")
    try:
        from backend.routes.external import get_weather, get_aqi
        weather = get_weather(city)
        aqi = get_aqi(city)
    except Exception:
        weather = {}
        aqi = 100

    result = run_simulation(scenario, base_income, weather=weather, aqi=aqi)
    return jsonify(result)
