from flask import Blueprint, jsonify, render_template
from backend.state import LIVE_TRAFFIC_DATA,HUB_MODE

dashboard_bp = Blueprint("dashboard",__name__)


@dashboard_bp.route("/dashboard")
def dashboard_page():
    return render_template("cam_dashboard.html")

@dashboard_bp.route("/api/dashboard")
def dashboard_data():
    hub_id = 1

    cameras = LIVE_TRAFFIC_DATA.get(hub_id,{})

    total = 0
    cam_data = {}

    for cam_id, cam in cameras.items():
        vehicles = cam.get("vehicle_count",0)
        density = cam.get("density","LOW")
        light = cam.get("light","RED")

        total += vehicles

        cam_data[cam_id] = {
            "vehicles": vehicles,
            "density": density,
            "light": light
        }

    return jsonify({
        "hub": hub_id,
        "mode": HUB_MODE.get(hub_id,"AUTO"),
        "total_vehicles": total,
        "cameras": cam_data
    })