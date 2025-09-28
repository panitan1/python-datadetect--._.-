import cv2

# เปิดวิดีโอ
cap = cv2.VideoCapture("video.mp4")   # ถ้าเป็นกล้องสดใช้ 0

# อ่านเฟรมแรก
ret, frame = cap.read()

if ret:
    # บันทึกเป็นไฟล์ภาพ
    cv2.imwrite("capture.jpg", frame)
    print("✅ บันทึกภาพแล้ว: capture.jpg")
else:
    print("❌ อ่านเฟรมไม่สำเร็จ")

cap.release()
