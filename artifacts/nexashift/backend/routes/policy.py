from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users
from backend.services.pricing_engine import compute_premium, compute_coverage

policy_bp = Blueprint("policy", __name__)

@policy_bp.route("/policy/<user_id>", methods=["GET"])
def get_policy(user_id):
    user = users.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user_id": user_id,
        "name": user["name"],
        "coverage_type": "standard",
        "premium": user["premium"],
        "coverage": user["coverage"],
        "risk_score": user["risk_score"],
        "status": "ACTIVE",
        "city": user["city"],
        "work_type": user["work_type"],
    })

@policy_bp.route("/policy/create", methods=["POST"])
def create_policy():
    data = request.get_json()
    user_id = data.get("user_id")
    coverage_type = data.get("coverage_type", "standard")

    user = users.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    premium = compute_premium(user["income"], user["risk_score"])
    coverage = compute_coverage(user["income"], coverage_type)
    user["premium"] = premium
    user["coverage"] = coverage

    return jsonify({
        "user_id": user_id,
        "coverage_type": coverage_type,
        "premium": premium,
        "coverage": coverage,
        "status": "ACTIVE",
    })
