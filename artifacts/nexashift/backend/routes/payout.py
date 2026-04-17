"""
NexaShift Phase 3 — UPI Payout Pipeline Routes
Simulates realistic UPI bank transfer lifecycle.
"""
from flask import Blueprint, request, jsonify
from backend.utils.memory_store import users, payout_logs
from backend.services.payout_engine import (
    initiate_payout, advance_payout_state, get_payout, get_user_payouts
)

payout_bp = Blueprint("payout", __name__)


@payout_bp.route("/payout/initiate", methods=["POST"])
def payout_initiate():
    """Initiate a UPI payout for an approved claim."""
    data     = request.get_json()
    user_id  = data.get("user_id")
    claim_id = data.get("claim_id")
    amount   = int(data.get("amount", 0))

    user = users.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    payout = initiate_payout(claim_id, amount, user)
    return jsonify(payout)


@payout_bp.route("/payout/advance/<txn_id>", methods=["POST"])
def payout_advance(txn_id):
    """Advance payout to next state (polling simulation)."""
    payout = advance_payout_state(txn_id)
    if not payout:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify(payout)


@payout_bp.route("/payout/status/<txn_id>", methods=["GET"])
def payout_status(txn_id):
    payout = get_payout(txn_id)
    if not payout:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify(payout)


@payout_bp.route("/payout/history/<user_id>", methods=["GET"])
def payout_history(user_id):
    payouts = get_user_payouts(user_id)
    return jsonify(sorted(payouts, key=lambda p: p.get("initiated_at", ""), reverse=True))
