# backend/routes/analysis_routes.py

from flask import Blueprint, render_template, jsonify
from backend.state import LIVE_TRAFFIC_DATA

analysis_bp = Blueprint("analysis", __name__)

# ================= PAGE LOAD =================
@analysis_bp.route("/analysis")
def analysis_dashboard():
    return render_template("analysis.html")


# ================= REAL-TIME API =================
@analysis_bp.route("/analysis_data/<hub_id>")
def analysis_data(hub_id):

    from backend.database import Camera
    from backend.state import LIVE_TRAFFIC_DATA
    from flask import jsonify

    # ✅ Get only cameras belonging to this hub
    cameras = Camera.query.filter_by(hub_id=hub_id).all()

    live_density = {}
    cumulative = {}
    smart_time = []
    traditional_time = []

    for cam in cameras:

        data = LIVE_TRAFFIC_DATA.get(cam.id, {})

        lane_name = f"Lane {cam.id}"
        count = data.get("vehicle_count", 0)

        live_density[lane_name] = count

        cumulative[lane_name] = {
            "cars": data.get("cars", 0),
            "buses": data.get("buses", 0),
            "trucks": data.get("trucks", 0),
            "motorcycles": data.get("motorcycles", 0),
            "ambulances": data.get("ambulances", 0)
        }

        smart_time.append(max(10, min(count, 30)))
        traditional_time.append(30)

    return jsonify({
        "lanes": list(live_density.keys()),
        "live_density": live_density,
        "cumulative": cumulative,
        "smart_time": smart_time,
        "traditional_time": traditional_time
    })