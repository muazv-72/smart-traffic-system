import time

from backend.ai.detection import detect_vehicles_and_calculate_score
from backend.database import Camera, Hub, db
from backend.state import HUB_MODE, HUB_STATES, LIVE_TRAFFIC_DATA


# =================================================
# AUTO MODE FSM (MULTI-HUB SAFE VERSION)
# =================================================
def run_auto_mode(app):
    """Run the automatic traffic control mode (multi-hub safe)."""
    print("🚀 Auto Mode Thread Started!")

    with app.app_context():
        while True:
            try:
                hubs = Hub.query.all()

                for hub in hubs:
                    mode = HUB_MODE.get(hub.id, "auto")
                    if mode != "auto":
                        if hub.id in HUB_STATES:
                            del HUB_STATES[hub.id]
                        print(f"⛔ AUTO STOPPED → Hub {hub.name} in MANUAL")
                        continue

                    cameras = Camera.query.filter_by(hub_id=hub.id).all()
                    if not cameras:
                        continue

                    # Initialize hub state if not exists
                    if hub.id not in HUB_STATES:
                        HUB_STATES[hub.id] = {
                            "current_index": 0,
                            "state": "SCAN",
                            "timer_start": 0,
                            "duration": 0,
                        }

                    st = HUB_STATES[hub.id]
                    now = time.time()
                    current_cam = cameras[st["current_index"] % len(cameras)]

                    # =========================
                    # SCAN STATE
                    # =========================
                    if st["state"] == "SCAN":
                        print(f"\n🔍 SCANNING HUB: {hub.name} | Mode: AUTO")

                        # Make all cameras RED first
                        for c in cameras:
                            c.light = "red"

                        emergency_cam = None
                        best_cam = None
                        best_score = -1

                        for cam in cameras:
                            score, count, is_emergency = (
                                detect_vehicles_and_calculate_score(cam)
                            )
                            cam.vehicles = count

                            LIVE_TRAFFIC_DATA[cam.id] = {
                                "vehicles": count,
                                "is_emergency": is_emergency,
                            }

                            # 🚑 Emergency Priority
                            if is_emergency:
                                emergency_cam = cam
                                print(
                                    f"[{hub.name}] 🚑 AMBULANCE DETECTED IN "
                                    f"{cam.name}"
                                )
                                break

                            # Normal traffic scoring
                            if score > best_score:
                                best_score = score
                                best_cam = cam

                        # =========================
                        # Decision Making
                        # =========================
                        if emergency_cam:
                            current_cam = emergency_cam
                            calc_time = 60
                            current_cam.light = "green"
                            db.session.commit()

                            print(
                                f"[{hub.name}] 🚑 AMBULANCE DETECTED IN "
                                f"{current_cam.name}"
                            )
                            print(
                                f"[{hub.name}] 🚦 GREEN GIVEN TO "
                                f"{current_cam.name} (AMBULANCE PRIORITY)"
                            )
                        else:
                            if best_cam is None:
                                continue

                            current_cam = best_cam
                            calc_time = (best_score * 1.5) + 5
                            calc_time = max(5, min(calc_time, 60))

                            current_cam.light = "green"
                            db.session.commit()

                        print(
                            f"[{hub.name}] 🚦 GREEN GIVEN TO {current_cam.name}"
                        )

                        # Save state for FSM
                        st["state"] = "GREEN"
                        st["duration"] = calc_time
                        st["timer_start"] = now

                    # =========================
                    # GREEN STATE
                    # =========================
                    elif st["state"] == "GREEN":
                        if now - st["timer_start"] >= st["duration"]:
                            current_cam.light = "yellow"
                            db.session.commit()

                            st["state"] = "YELLOW"
                            st["duration"] = 3
                            st["timer_start"] = now

                        print(f"[{hub.name}] 🟡 YELLOW -> {current_cam.name}")

                    # =========================
                    # YELLOW STATE
                    # =========================
                    elif st["state"] == "YELLOW":
                        if now - st["timer_start"] >= st["duration"]:
                            current_cam.light = "red"
                            db.session.commit()

                            print(f"[{hub.name}] 🔴 RED -> {current_cam.name}")

                    # Move to next camera
                st["current_index"] = (st["current_index"] + 1) % len(cameras)
                st["state"] = "SCAN"

                time.sleep(1)

            except Exception as e:
                print(f"❌ Auto Mode Error: {e}")
                time.sleep(2)
