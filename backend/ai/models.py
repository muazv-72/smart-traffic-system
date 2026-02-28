from ultralytics import YOLO
print("⏳ Loading AI Models...")
try:
    model_traffic = YOLO('yolov8n.pt')
    model_ambulance = YOLO('ambulance.pt')
    print("✅ Models Loaded Successfully!")
except Exception as e:
    print(f"❌ Error loading models: {e}")
    model_traffic = None
    model_ambulance = None
