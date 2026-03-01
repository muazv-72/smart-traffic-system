import time

import cv2
import numpy as np

from backend.ai.models import model_ambulance, model_traffic


# =================================================
# AI DETECTION
# =================================================
def detect_vehicles_and_calculate_score(cam):

    if not model_traffic:
        return 0, 0, False

    cap = cv2.VideoCapture(cam.ip)

    if cam.ip.endswith(".mp4") or cam.ip.endswith(".avi"):
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0:
            current_frame = int(time.time() * 10) % total_frames
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

    success, frame = cap.read()
    cap.release()

    if not success:
        return 0, 0, False

    roi_points = None
    if cam.roi:
        try:
            coords = list(map(int, cam.roi.split(",")))
            roi_points = np.array(coords, dtype=np.int32).reshape((-1, 1, 2))
        except Exception:
            pass

    # 🚑 Ambulance Detection
    is_emergency = False
    if model_ambulance:
        amb_results = model_ambulance(frame, conf=0.5, verbose=False)
        if amb_results and len(amb_results[0].boxes) > 0:
            is_emergency = True

    results = model_traffic(frame, verbose=False)

    total_score = 0
    vehicle_count = 0

    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) in [2, 3, 5, 7]:

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                if roi_points is not None:
                    if cv2.pointPolygonTest(roi_points, (cx, cy), False) < 0:
                        continue

                width = x2 - x1
                height = y2 - y1
                area = width * height

                weight = 1.0
                if area < 3000:
                    weight = 0.5
                elif area > 10000:
                    weight = 3.0

                total_score += weight
                vehicle_count += 1

    return total_score, vehicle_count, is_emergency
