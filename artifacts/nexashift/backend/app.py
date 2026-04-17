import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.routes.auth       import auth_bp
from backend.routes.policy     import policy_bp
from backend.routes.claim      import claim_bp
from backend.routes.trigger    import trigger_bp
from backend.routes.map        import map_bp
from backend.routes.decision   import decision_bp
from backend.routes.simulation import simulation_bp
from backend.routes.external   import external_bp
from backend.routes.scenario_lab import scenario_lab_bp
# Phase 3
from backend.routes.admin        import admin_bp
from backend.routes.ml           import ml_bp
from backend.routes.autopilot    import autopilot_bp
from backend.routes.payout       import payout_bp
from backend.routes.fraud_analyze import fraud_bp
from backend.routes.microzones   import microzones_bp
from backend.routes.insights     import insights_bp
from backend.income_protection   import protection_bp
from backend.routes.ml_observatory import observatory_bp

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

app.register_blueprint(auth_bp)
app.register_blueprint(policy_bp)
app.register_blueprint(claim_bp)
app.register_blueprint(trigger_bp)
app.register_blueprint(map_bp)
app.register_blueprint(decision_bp)
app.register_blueprint(simulation_bp)
app.register_blueprint(external_bp)
app.register_blueprint(scenario_lab_bp)
# Phase 3
app.register_blueprint(admin_bp)
app.register_blueprint(ml_bp)
app.register_blueprint(autopilot_bp)
app.register_blueprint(payout_bp)
app.register_blueprint(fraud_bp)
app.register_blueprint(microzones_bp)
app.register_blueprint(insights_bp)
app.register_blueprint(protection_bp)
app.register_blueprint(observatory_bp)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
