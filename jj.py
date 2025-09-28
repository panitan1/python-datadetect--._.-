import cv2
import time
from ultralytics import YOLO

# ---- CONFIG ----
CAMERA_SRC = 0            # เปลี่ยนเป็น RTSP/ไฟล์ได้ เช่น "rtsp://user:pass@ip:554/stream"
MODEL_PATH = "yolo11n.pt" # หรือโมเดลของคุณเอง .pt
MODEL_PATH2 = "yolo11n.pt" 
IMG_SIZE = 640
CONF_THRES = 0.4

# ---- LOAD MODEL ----
model = YOLO(MODEL_PATH)
mode2 = YOLO(MODEL_PATH2)
# ถ้ามี CUDA จะใช้เองอัตโนมัติ (Ultralytics จะเลือกให้) ไม่ต้อง .to("cuda")

# ---- OPEN CAMERA ----
cap = cv2.VideoCapture(CAMERA_SRC)
if not cap.isOpened():
    raise RuntimeError(f"เปิดกล้องไม่สำเร็จ: {CAMERA_SRC}")

prev = time.time()
fps = 0.0

while True:
    ok, frame = cap.read()
    if not ok:
        print("อ่านภาพจากกล้องไม่สำเร็จ")
        break

    # ---- INFERENCE ----
    results = model(frame, imgsz=IMG_SIZE, conf=CONF_THRES, verbose=False , classes = [1])
    annotated = results[0].plot()  

    results = mode2(frame, imgsz=IMG_SIZE, conf=CONF_THRES, verbose=False , classes = [0])
    annotated = results[0].plot() 
    
    # ---- FPS ----
    now = time.time()
    dt = now - prev
    prev = now
    fps = 0.9*fps + 0.1*(1.0/dt if dt > 0 else 0)  # EMA ให้ค่าลื่นขึ้น
    cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

    cv2.imshow("YOLO Live", annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
