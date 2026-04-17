"""
NexaShift Phase 3 — UPI Payout Simulation Engine
Simulates realistic bank/UPI transaction lifecycle with state machine.
"""
import uuid
import random
from datetime import datetime
from backend.utils.memory_store import payout_logs

BANKS = ["HDFC Bank", "SBI", "ICICI Bank", "Kotak", "Axis Bank",
         "Paytm Payments Bank", "PhonePe", "Google Pay"]

PAYOUT_STATES = ["INITIATED", "PROCESSING", "FRAUD_CHECK", "APPROVED", "SUCCESS"]

STATE_MESSAGES = {
    "INITIATED":    "Payout request received. Validating claim...",
    "PROCESSING":   "Connecting to UPI payment network...",
    "FRAUD_CHECK":  "Running AI fraud verification (3-second scan)...",
    "APPROVED":     "Fraud check passed. Initiating bank transfer...",
    "SUCCESS":      "₹ credited to your UPI account successfully!",
}

# Estimated time (seconds) to reach each state from previous
STATE_DURATIONS = {
    "INITIATED":    2,
    "PROCESSING":   5,
    "FRAUD_CHECK":  3,
    "APPROVED":     8,
    "SUCCESS":      30,
}


def _upi_id(name: str) -> str:
    clean = "".join(c for c in name.lower() if c.isalpha())[:10]
    suffix = random.choice(["@okaxis", "@ybl", "@ibl", "@okicici", "@paytm", "@upi"])
    return clean + suffix


def initiate_payout(claim_id: str, amount: int, user: dict) -> dict:
    """Create a new payout record and set state to INITIATED."""
    txn_id = "TXN" + uuid.uuid4().hex[:10].upper()
    bank   = random.choice(BANKS)
    upi_id = _upi_id(user.get("name", "worker"))

    payout = {
        "txn_id":        txn_id,
        "claim_id":      claim_id,
        "user_id":       user.get("user_id", ""),
        "amount":        amount,
        "upi_id":        upi_id,
        "bank":          bank,
        "state":         "INITIATED",
        "state_index":   0,
        "message":       STATE_MESSAGES["INITIATED"],
        "initiated_at":  datetime.utcnow().isoformat(),
        "completed_at":  None,
        "estimated_min": random.randint(2, 8),
        "state_history": [{"state": "INITIATED", "ts": datetime.utcnow().isoformat()}],
    }
    payout_logs[txn_id] = payout
    return payout


def advance_payout_state(txn_id: str) -> dict | None:
    """Move payout to next state. Idempotent if already at SUCCESS."""
    payout = payout_logs.get(txn_id)
    if not payout:
        return None

    idx = payout["state_index"]
    if idx >= len(PAYOUT_STATES) - 1:
        return payout  # Already at SUCCESS

    next_idx   = idx + 1
    next_state = PAYOUT_STATES[next_idx]
    payout["state"]         = next_state
    payout["state_index"]   = next_idx
    payout["message"]       = STATE_MESSAGES[next_state]
    payout["state_history"].append({
        "state": next_state,
        "ts":    datetime.utcnow().isoformat(),
    })
    if next_state == "SUCCESS":
        payout["completed_at"] = datetime.utcnow().isoformat()

    return payout


def get_payout(txn_id: str) -> dict | None:
    return payout_logs.get(txn_id)


def get_user_payouts(user_id: str) -> list:
    return [p for p in payout_logs.values() if p.get("user_id") == user_id]
