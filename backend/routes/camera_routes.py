from flask import Blueprint, render_template, request, Response, jsonify, session
from backend.auth.decorators import login_required
from backend.database import db, Hub, Camera
from backend.state import LIVE_TRAFFIC_DATA, HUB_STATES, HUB_MODE, GLOBAL_MODE
from backend.ai.models import model_traffic, model_ambulance
from backend.ai.auto_mode import run_auto_mode

import cv2
import time
import threading
import uuid
import numpy as np
import base64


camera_bp = Blueprint("camera", __name__)

# =================================================
# BACKGROUND THREAD
# =================================================
def start_background_thread(app):
    t = threading.Thread(target=run_auto_mode, args=(app,))
    t.daemon = True
    t.start()

@camera_bp.route("/hub/<hub_id>")
@login_required
def hub(hub_id):
    hub = Hub.query.get_or_404(hub_id)
    cameras = Camera.query.filter_by(hub_id=hub_id).all()
    cameras_dict = {c.id: c for c in cameras}
    mode = HUB_MODE.get(hub_id,"auto")
    return render_template(
        "hub.html", 
        hub_id=hub.id, 
        hub_name=hub.name, 
        cameras=cameras_dict, 
        mode = mode, 
        role=session.get("role")
    )

# Snapshot for ROI Drawing Tool
@camera_bp.route("/get_snapshot", methods=["POST"])
def get_snapshot():
    path = request.json.get("ip")
    cap = cv2.VideoCapture(path)
    success, frame = cap.read()
    cap.release()
    if not success: return jsonify({"error": "Error reading video"}), 400
    _, buffer = cv2.imencode('.jpg', frame)
    return jsonify({"image": base64.b64encode(buffer).decode('utf-8')})

@camera_bp.route("/set_mode", methods=["POST"])
@login_required
def set_mode_route():
    data=request.json

    if not data:
        return jsonify({"error":"No data received"}),400
    
    hub_id=data["hub_id"]

    mode=data["mode"]

    if not hub_id:
        return jsonify({"error": "hub_id missing"}), 400

    if not mode:
        return jsonify({"error": "mode missing"}), 400

    HUB_MODE[hub_id]=mode

    if hub_id in HUB_STATES:
        del HUB_STATES[hub_id]

    print(f"⚙ Mode Changed → Hub {hub_id} = {mode}")

    return jsonify({"success":True})

@camera_bp.route("/add_camera", methods=["POST"])
@login_required
def add_camera():
    data = request.json
    new_id = f"cam_{uuid.uuid4().hex[:6]}"
    new_cam = Camera(id=new_id, name=data["name"], ip=data["ip"], hub_id=data["hub_id"], roi=data.get("roi"), light="red")
    db.session.add(new_cam)
    db.session.commit()
    return jsonify({"ok": True})

@camera_bp.route("/edit_camera", methods=["POST"])
@login_required
def edit_camera():
    data = request.json
    cam = Camera.query.get(data["id"])
    if cam:
        cam.name = data.get("name", cam.name)
        cam.ip = data.get("ip", cam.ip)
        if "roi" in data: cam.roi = data["roi"]
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404

@camera_bp.route("/delete_camera", methods=["POST"])
@login_required
def delete_camera():
    data = request.json
    cam = Camera.query.get(data["id"])
    if cam:
        db.session.delete(cam)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404

# --- VIDEO STREAM ROUTE (With Visualization Fixes) ---
@camera_bp.route("/video/<cid>")
def video(cid):
    cam = Camera.query.get(cid)
    if not cam:
        return "", 404

    # Parse ROI
    roi_points = []
    if cam.roi:
        try:
            coords = list(map(int, cam.roi.split(',')))
            roi_points = np.array(coords, dtype=np.int32).reshape((-1, 1, 2))
        except:
            pass

    def generate(path):
        cap = cv2.VideoCapture(path)

        while True:
            success, frame = cap.read()
            if not success:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Draw ROI
            if len(roi_points) > 0:
                cv2.polylines(frame, [roi_points], True, (0, 0, 255), 3)

            # Initialize counters
            car_count = 0
            bus_count = 0
            truck_count = 0
            motorcycle_count = 0
            ambulance_count = 0

            # =====================================================
            # 🚗 TRAFFIC MODEL (COCO)
            # =====================================================
            if model_traffic:
                results_traffic = model_traffic(
                    frame,
                    conf=0.25,
                    iou=0.5,
                    agnostic_nms=True,
                    verbose=False
                )

                for r in results_traffic:
                    for box in r.boxes:

                        cls = int(box.cls[0])
                        cls_name = model_traffic.names[cls].lower()

                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                        # ROI filtering
                        if len(roi_points) > 0:
                            if cv2.pointPolygonTest(roi_points, (cx, cy), False) < 0:
                                continue

                        # Count vehicles
                        if cls_name == "car":
                            car_count += 1
                        elif cls_name == "motorcycle":
                            motorcycle_count += 1
                        elif cls_name == "bus":
                            bus_count += 1
                        elif cls_name == "truck":
                            truck_count += 1

                        # Draw green box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # =====================================================
            # 🚑 AMBULANCE MODEL (CUSTOM)
            # =====================================================
            if model_ambulance:
                results_ambulance = model_ambulance(
                    frame,
                    conf=0.25,
                    iou=0.5,
                    verbose=False
                )

                for r in results_ambulance:
                    for box in r.boxes:

                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                        # ROI filtering
                        if len(roi_points) > 0:
                            if cv2.pointPolygonTest(roi_points, (cx, cy), False) < 0:
                                continue

                        ambulance_count += 1

                        # Draw RED box for ambulance
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

            # =====================================================
            # 🔢 TOTAL COUNT
            # =====================================================
            total_count = (
                car_count +
                bus_count +
                truck_count +
                motorcycle_count +
                ambulance_count
            )

            # =====================================================
            # 🌍 UPDATE GLOBAL LIVE DATA
            # =====================================================
            LIVE_TRAFFIC_DATA[cid] = {
                "vehicle_count": total_count,
                "vehicles": total_count,
                "cars": car_count,
                "buses": bus_count,
                "trucks": truck_count,
                "motorcycles": motorcycle_count,
                "ambulances": ambulance_count,
                "is_emergency": ambulance_count > 0
            }

            # Encode frame
            _, buffer = cv2.imencode(".jpg", frame)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                buffer.tobytes() +
                b"\r\n"
            )

    return Response(
        generate(cam.ip),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

# --- POLLING STATE (Includes Ambulance Flag) ---
@camera_bp.route("/state")
def state():
    all_cams = Camera.query.all()
    cams_dict = {}
    for c in all_cams:
        live_data = LIVE_TRAFFIC_DATA.get(c.id, {})
        
        # Handle fallback for first run
        if isinstance(live_data, int):
            count = live_data
            emb = False
        else:
            count = live_data.get("vehicles", c.vehicles)
            emb = live_data.get("is_emergency", False)

        cams_dict[c.id] = {
            "light": c.light, 
            "vehicles": count,
            "is_emergency": emb # Send flag to frontend
        }
    return jsonify({ "cameras": cams_dict, "mode": GLOBAL_MODE })

@camera_bp.route("/set_green", methods=["POST"])
@login_required
def set_green():

    data = request.json
    cam_id = data.get("id")

    if not cam_id:
        return jsonify({"error":"Camera ID missing"}),400

    target_cam = Camera.query.get(cam_id)

    if not target_cam:
        return jsonify({"error":"Camera not found"}),404


    # ✅ Check HUB MODE
    hub_mode = HUB_MODE.get(target_cam.hub_id,"auto")

    if hub_mode == "auto":
        print("❌ Manual blocked → Hub in AUTO mode")
        return jsonify({"error":"Hub is in Auto Mode"}),403


    # ✅ Manual Control Allowed
    cameras = Camera.query.filter_by(hub_id=target_cam.hub_id).all()

    for c in cameras:
        c.light="red"

    target_cam.light="green"

    db.session.commit()

    print("✅ Manual GREEN:", target_cam.name)

    return jsonify({"success":True})

@camera_bp.route("/api/camera-status/<hub_id>")
def get_camera_status(hub_id):
    hub = Hub.query.get_or_404(hub_id)

    data = {}

    for cam in hub.cameras:
        live_data = LIVE_TRAFFIC_DATA.get(cam.id,{})

        data[cam.id] = {
            "vehicles": live_data.get("vehicles",0),
            "light": cam.light
        }
    return jsonify(data)

@camera_bp.route("/toggle_light", methods=["POSt"])
@login_required
def toggle_light():
    data = request.get_json()

    cam_id = data["camera_id"]
    hub_id = data["hub_id"]

    if not cam_id or not hub_id:
        return jsonify({"success":False,"error":"missing data"}),400
    
    cam = Camera.query.get(cam_id)

    if not cam:
        return jsonify({"success":False,"error":"Camera not found"}),404
    
    hub_mode = HUB_MODE.get(hub_id,"auto")

    if hub_mode == "auto":
        return jsonify({"error":"Hub is in Auto mode"}),403
    
    
    cameras = Camera.query.filter_by(hub_id=hub_id).all()
    
    if cam.light != "green":

        for c in cameras:
            c.light = "red"

        cam.light = "green"
        print(f"🟢 Manual GREEN -> {cam.name}")

    else:
        
        cam.light = "red"
        print(f"🔴 Manual RED -> {cam.name}")
    
    db.session.commit()

    return jsonify({"success":True})