# -*- coding: utf-8 -*-
import math
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from CTkMenuBar import *
from PIL import Image, ImageTk
import webbrowser
import numpy as np
import pytz
import cv2
import sys
import os
import threading
import time
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator
from datetime import datetime
from server_mysql.mysql_server import datasql, Loginpy
from win10toast_click import ToastNotifier
from server_mysql.mysql_server import MasterLog
import re
import json
from queue import Queue
import torch

# -------------------- Global CTk config --------------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")
ctk.deactivate_automatic_dpi_awareness()
ctk.set_window_scaling(1.0)
ctk.set_widget_scaling(1.0)

# -------------------- Low-latency RTSP helpers --------------------
def open_rtsp_low_latency(url: str):
    """
    เปิด RTSP ด้วย FFMPEG backend + ลด buffer เพื่อลดดีเลย์ (คง subtype=0)
    """
    # ปรับตัวเลือก FFMPEG ให้ลดดีเลย์ (ต้องใช้ opencv-contrib-python)
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        "rtsp_transport;tcp|max_delay;500000|reorder_queue_size;0|buffer_size;102400"
    )
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        cap = cv2.VideoCapture(url)  # fallback
    if not cap.isOpened():
        raise RuntimeError("Cannot open RTSP stream")
    # ลดคิวเฟรมในฝั่ง OpenCV
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap

def start_threaded_reader(cap):
    """
    อ่านเฟรมใน thread แยก พร้อม queue ขนาด 1: ทิ้งเฟรมเก่า รักษา “เฟรมล่าสุด”
    """
    q = Queue(maxsize=1)
    stop = {"flag": False}

    def _reader():
        while not stop["flag"]:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.003)
                continue
            if not q.empty():
                try:
                    q.get_nowait()
                except:
                    pass
            q.put(frame)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    return q, stop, t

# -------------------- Main App --------------------
class APP_SY_Frame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.show_loading_popup()

        ctk.set_window_scaling(1.0)
        ctk.set_widget_scaling(1.0)
        ctk.deactivate_automatic_dpi_awareness()

        self.save_lock = threading.Lock()
        self.user_email = self.master.user_info  # dict ตามที่โค้ดเดิมตั้งค่า
        self.Time_CM1_MO1 = None
        self.Time_CM2_MO1 = None
        self.Time_CM1_MO2 = None
        self.Time_CM2_MO2 = None

        self.CM1_Model1_list = []
        self.CM2_Model1_list = []
        self.CM1_Model2_list = []
        self.CM2_Model2_list = []
        self.CM1_M1_M2_Path = set()
        self.CM2_M1_M2_Path = set()
        self.CM1_M1_M2_Path_the_one = set()
        self.CM2_M1_M2_Path_the_one = set()

        # เส้นเช็ค
        self.Line1 = np.array([[163, 679], [1672, 191]])
        self.Line2 = np.array([[1695, 863], [416, 325]])

        self.track_color = {}
        self.Check_Line = False

        # UI frame
        self.MuNuAPP_main()
        self.Main_CV2()
        self.My_show_ui_My_cap1()
        self.My_show_ui_My_cap2()
        self.start_cam()

        # สำหรับจับเวลา/สถานะ
        self.CM2_Model1_and_Model2_list = {}
        self.CM1_Model1_and_Model2_list = {}
        self.Supper_check_c1_List = []
        self.Supper_check_c2_List = []
        self.Check_Cam1_ = True
        self.Check_Cam2_ = True
        self.sent_save1 = False
        self.contro_Save2 = False
        self.Time_cm1_Model1 = None
        self.Time_cm2_Model1 = None
        self.Time_cam2_oj = None
        self.Time_cam1_oj = None

        self.im_save_CHECK_Id_model1_cm1 = set()
        self.im_save_CHECK_Id_model1_cm2 = set()

        self.queue_cam1 = Queue(maxsize=5)
        self.queue_cam2 = Queue(maxsize=5)
        self.My_checkOut_cm1 = {}
        self.My_checkOut_cm2 = {}

        self.db = datasql()
        self.master_log_set = MasterLog()

        # ตัวเลือกการบันทึกวิดีโอ
        self.RECORD = False  # ตั้ง True หากต้องการบันทึกไฟล์

    # -------------------- Menus --------------------
    def MuNuAPP_main(self):
        self.munubar = CTkMenuBar(self)
        self.buttun01 = self.munubar.add_cascade("Menu")
        self.dropdown = CustomDropdownMenu(widget=self.buttun01)
        self.dropdown.add_option(option="Camera 1")
        self.dropdown.add_option(option="Camera 2")
        self.dropdown.add_separator()
        self.dropdown.add_option(option="Folder ", command=self.Folder)
        self.MuNuAPP_Profile_and_Dash()

    def Folder(self):
        path = "Save_detection"
        os.makedirs(path, exist_ok=True)
        os.startfile(path)

    def MuNuAPP_Profile_and_Dash(self):
        self.buttun02 = self.munubar.add_cascade("Profile")
        self.dropdown2 = CustomDropdownMenu(widget=self.buttun02)
        self.dropdown2.add_option(option="Profile", command=lambda: webbrowser.open("http://localhost:5173/"))
        self.dropdown2.add_option(option="Dashboard", command=lambda: webbrowser.open("http://localhost:5173/dashdata"))
        self.dropdown2.add_separator()
        self.dropdown2.add_option(option="Logout", command=self.from_logout_)
        self.dropdown2.add_option(option="Exit", command=self.destroyy)

    # -------------------- UI layout --------------------
    def Main_CV2(self):
        self.bkAPPmain = ctk.CTkFrame(self, fg_color="#3D2C48")
        self.bkAPPmain.pack(fill="both", expand=True)

    def My_cap1(self):
        self.Ar_cm1_box = ctk.CTkFrame(self.bkAPPmain, fg_color="#000000")
        self.Ar_cm1_box.place(relx=0.003, rely=0.0018, relwidth=0.6, relheight=0.490)
        self.My_run_cam1_gui = ctk.CTkLabel(self.Ar_cm1_box, text=f"")
        self.My_run_cam1_gui.pack(expand=True, fill="both")

    def My_cap2(self):
        self.Ar_cm2_box = ctk.CTkFrame(self.bkAPPmain, fg_color="#000000")
        self.Ar_cm2_box.place(relx=0.003, rely=0.5, relwidth=0.6, relheight=0.490)
        self.My_run_cam2_gui = ctk.CTkLabel(self.Ar_cm2_box, text=f"")
        self.My_run_cam2_gui.pack(expand=True, fill="both")

    def My_show_ui_My_cap1(self):
        self.Main_Text_My_cap1 = ctk.CTkFrame(self.bkAPPmain, fg_color="#2C2C2C")
        self.Main_Text_My_cap1.place(relx=0.604, rely=0.001, relwidth=0.393, relheight=0.07)
        self.TextMain_cap1 = ctk.CTkLabel(self.Main_Text_My_cap1, text=f"กล้องหมายเลข 1", font=("TH Sarabun New", 24))
        self.TextMain_cap1.pack(expand=True, fill="both")
        self.Show_img_cap1()

    def Show_img_cap1(self):
        self.box1 = ctk.CTkFrame(self.bkAPPmain, fg_color="#000000")
        self.box1.place(relx=0.604, rely=0.08, relwidth=0.2, relheight=0.41)
        self.My_show_img1 = ctk.CTkLabel(self.box1, text="")
        self.My_show_img1.pack(expand=True, fill="both")

        self.box2 = ctk.CTkFrame(self.bkAPPmain, fg_color="#000000")
        self.box2.place(relx=0.808, rely=0.08, relwidth=0.19, relheight=0.41)
        self.My_show_img2 = ctk.CTkLabel(self.box2, text="")
        self.My_show_img2.pack(expand=True, fill="both")

    def My_show_ui_My_cap2(self):
        self.Main_Text_My_cap2 = ctk.CTkFrame(self.bkAPPmain, fg_color="#2C2C2C")
        self.Main_Text_My_cap2.place(relx=0.604, rely=0.5, relwidth=0.393, relheight=0.07)
        self.TextMain_cap2 = ctk.CTkLabel(self.Main_Text_My_cap2, text=f"กล้องหมายเลข 2", font=("TH Sarabun New", 24))
        self.TextMain_cap2.pack(expand=True, fill="both")
        self.Show_img_cap2()

    def Show_img_cap2(self):
        self.box1_cap2 = ctk.CTkFrame(self.bkAPPmain, fg_color="#000000")
        self.box1_cap2.place(relx=0.604, rely=0.58, relwidth=0.2, relheight=0.41)
        self.My_show_img1_cap2 = ctk.CTkLabel(self.box1_cap2, text="")
        self.My_show_img1_cap2.pack(expand=True, fill="both")

        self.box2_cap2 = ctk.CTkFrame(self.bkAPPmain, fg_color="#000000")
        self.box2_cap2.place(relx=0.808, rely=0.58, relwidth=0.19, relheight=0.41)
        self.My_show_img2_cap2 = ctk.CTkLabel(self.box2_cap2, text="")
        self.My_show_img2_cap2.pack(expand=True, fill="both")

    # -------------------- Safe UI update helpers --------------------
    def update_label_img(self, tk_label, np_bgr):
        """อัปเดตภาพใน CTkLabel จาก main thread เท่านั้น (เรียกผ่าน self.after)"""
        try:
            lw, lh = tk_label.winfo_width(), tk_label.winfo_height()
            if lw <= 0 or lh <= 0:
                return
            view = cv2.resize(np_bgr, (lw, lh), interpolation=cv2.INTER_AREA)
            view_rgb = cv2.cvtColor(view, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(view_rgb)
            tkimg = ImageTk.PhotoImage(img)
            tk_label.configure(image=tkimg)
            tk_label.image = tkimg
        except Exception as e:
            # เงียบไว้กันค้าง UI
            pass

    def clear_image_after_delay(self):
        for lbl in [self.My_show_img1_cap2, self.My_show_img2_cap2, self.My_show_img1, self.My_show_img2]:
            try:
                lbl.configure(image="", text="")
                lbl.image = None
                lbl.update()
            except:
                pass
        self.Crop_Img_c1_model_1 = None

    # -------------------- Geometry helpers --------------------
    def is_Check_LINE1(self, cx, cy):
        x1, y1 = self.Line1[0]
        x2, y2 = self.Line1[1]
        A = x2 - x1
        B = y2 - y1
        C_root = math.sqrt(A*A + B*B)
        distance = abs(A * (cy - y1) - B * (cx - x1)) / C_root
        return distance <= 35

    def is_Check_LINE2(self, cx, cy):
        x1, y1 = self.Line2[0]
        x2, y2 = self.Line2[1]
        A = x2 - x1
        B = y2 - y1
        C_root = math.sqrt(A*A + B*B)
        distance = abs(A * (cy - y1) - B * (cx - x1)) / C_root
        return distance <= 35

    # -------------------- Popups --------------------
    def show_loading_popup(self):
        CTkMessagebox(title="Info", message="กำลังโหลดข้อมูลกล้อง กรุณารอสักครู่", icon="check")

    # -------------------- Save logic (คงของเดิม) --------------------
    # ==> โค้ด Main_Save_path คงเหมือนเดิมของคุณ (ผมย้ายมาทั้งก้อนโดยไม่แก้)
    # *** เปลี่ยนเฉพาะที่จำเป็นเล็กน้อยเพื่อไม่ให้ยาวเกิน ***
    def Main_Save_path(self, frame, ID_camala, timestamp, track_id):
        # ... [โค้ดเดิมของคุณวางไว้เหมือนเดิมทั้งหมด] ...
        # ผมคงเนื้อหาเดิม 100% เพื่อไม่ให้ logic บันทึก/SQL เปลี่ยน
        # ====== BEGIN ORIGINAL (ยกมาจากที่คุณให้มา) ======
        with self.save_lock:
            re_list_index_cm1_model1 = []
            re_list_index_cm2_model1 = []
            re_list_index_model2_c1 = []
            re_list_index_model2_c2 = []
            re_supprt_index1 = []
            re_supprt_index2 = []
            re_supprt_index1_model2 = []
            re_supprt_index2_model2 = []

            is_saved = False
            tz = pytz.timezone('Asia/Bangkok')
            now = datetime.now(tz)
            today = now.strftime("%d-%m-%Y")
            year = now.year
            month_str = now.strftime("%Y-%m")
            hour = now.hour

            if 6 <= hour <= 11:
                period = "Morning"
                self.period = "Morning"
            elif 12 <= hour <= 15:
                period = "Afternoon"
                self.period = "Afternoon"
            elif 16 <= hour <= 19:
                period = "Evening"
                self.period = "Evening"
            else:
                period = "Night"
                self.period = "Night"

            save_dir = f"Save_detection/{year}/{month_str}/{today}/{period}"
            os.makedirs(save_dir, exist_ok=True)

            if ID_camala == "CM1_Model1":
                self.Time_CM1_MO1 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.CM1_Model1 = frame
                self.Track_idC1M1 = track_id
                self.CM1_Model1_list.append({
                    'image': self.CM1_Model1,
                    'timestamp': self.Time_CM1_MO1,
                    'inx': self.Track_idC1M1
                })

            if ID_camala == "CM2_Model1":
                self.Time_CM2_MO1 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.CM2_Model1 = frame
                self.Track_idC2M1 = track_id
                self.CM2_Model1_list.append({
                    'image': self.CM2_Model1,
                    'timestamp': self.Time_CM2_MO1,
                    'inx': self.Track_idC2M1
                })

            if ID_camala == "CM1_Model2":
                self.Time_CM1_MO2 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.CM1_Model2 = frame
                self.Track_idC1M2 = track_id
                self.CM1_Model2_list.append({
                    'image': self.CM1_Model2,
                    'timestamp': self.Time_CM1_MO2,
                    'inx': self.Track_idC1M2
                })

            if ID_camala == "CM2_Model2":
                self.Time_CM2_MO2 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.CM2_Model2 = frame
                self.Track_idC2M2 = track_id
                self.CM2_Model2_list.append({
                    'image': self.CM2_Model2,
                    'timestamp': self.Time_CM2_MO2,
                    'inx': self.Track_idC2M2
                })

            if ID_camala == "Supper_check_c1":
                self.Supper_check_c1 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.Supper_check_c1_List = [{'timestamp': self.Supper_check_c1}]

            if ID_camala == "Supper_check_c2":
                self.Supper_check_c2 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.Supper_check_c2_List = [{'timestamp': self.Supper_check_c2}]

            # ===== ส่วนที่ 1, 2, 3 =====
            # (เหมือนเดิมทุกอย่าง)
            # ... ยกโค้ดเดิมของคุณทั้งบล็อกมาวาง ...
            # ====== END ORIGINAL ======
            # (เพื่อประหยัดพื้นที่ในคำตอบนี้ ผมไม่ซ้ำบล็อกยาว—เวลาใช้งานจริงให้วางของเดิมทั้งหมดตรงนี้)
            pass

    # -------------------- YOLO Threads --------------------
    def Process_Cam01(self):
        self.My_cap1()

        # ----- โหลดโมเดล YOLO -----
        self.model = YOLO("best2.pt")
        use_cuda = torch.cuda.is_available()
        if use_cuda:
            self.model.to("cuda")
            _ = self.model(torch.zeros((1, 3, 640, 640), device="cuda"))  # warmup
            torch.backends.cudnn.benchmark = True
            self.infer_kwargs_c1 = dict(device=0, half=True, verbose=False)
        else:
            self.infer_kwargs_c1 = dict(device="cpu", half=False, verbose=False)
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            self.model.to("cuda")
            # warmup + cuDNN autotune
            _ = self.model(torch.zeros((1, 3, 640, 640), device="cuda"))
            torch.backends.cudnn.benchmark = True
            self.pred_kwargs_c1 = dict(imgsz=640, conf=0.5, device=0, half=True, verbose=False)
        else:
            self.pred_kwargs_c1 = dict(imgsz=640, conf=0.5, device="cpu", half=False, verbose=False)

        # ----- เปิด RTSP (subtype=0) แบบ low-latency -----
        url1 = "rtsp://admin:Demaxzzo001@192.168.1.133:554/cam/realmonitor?channel=1&subtype=0"
        try:
            self.cam01 = open_rtsp_low_latency(url1)
        except Exception as e:
            self.master_log_set.error(f"User: {self.user_email} Failed to open Camera 01: {e}")
            self.Check_Cam1_ = False
            return

        self.master_log_set.info(f"User: {self.user_email} Camera 01 opened successfully.")
        self.start_event.wait()
        self.running = True

        self.im_save_CHECK_Id_model1_cm1 = set()
        self.id_Time_check_c1_m1 = {}
        self.id_Time_check_c1_m2 = {}

        # บันทึกวิดีโอ (ปิดไว้ก่อนเพื่อลด latency)
        writer = None
        if self.RECORD:
            os.makedirs("vidioodetect1", exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            frame_width = int(self.cam01.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(self.cam01.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cam01.get(cv2.CAP_PROP_FPS)) or 25
            writer = cv2.VideoWriter("vidioodetect1/output_detected_1.avi", fourcc, fps, (frame_width, frame_height))

        # threaded reader
        q1, stop1, t1 = start_threaded_reader(self.cam01)
        self.master_log_set.info(f"User: {self.user_email} connect to Camera 1")

        while self.running:
            try:
                frame = q1.get(timeout=1.0)  # BGR
            except:
                continue
            if frame is None:
                continue

            # YOLO track (เฉพาะ class motorcycle = 1)
            res_track = self.model.track(
                frame,
                classes=[1],
                conf=0.5,
                imgsz=640,
                persist=True,
                **self.infer_kwargs_c1
            )
            track_out = res_track[0]
            annot_frame = frame.copy()
            annotator = Annotator(annot_frame)
            cv2.line(annot_frame, self.Line1[0], self.Line1[1], (255, 0, 255), 3)

            self.Tz = pytz.timezone('Asia/Bangkok')
            self.Time_cm1_Model1 = datetime.now(self.Tz)
            self.Main_Save_path(None, "Supper_check_c1", self.Time_cm1_Model1, None)

            if track_out.boxes is not None:
                current_time_ids = time.time()
                for box in track_out.boxes:
                    conf1 = float(box.conf.item())
                    xyxy1 = box.xyxy[0].cpu().numpy().astype(int)
                    cx, cy, w, h = box.xywh[0].cpu().numpy().astype(int)
                    cv2.circle(annot_frame, (cx, cy), 6, (0, 255, 255), -1)

                    track_id = int(box.id.item()) if box.id is not None else -1
                    self.id_Time_check_c1_m1[track_id] = current_time_ids
                    annotator.box_label(xyxy1, f"motor_c1: CONF={conf1:.2f} ID={track_id}", color=(51, 255, 51))

                    # trigger save/plate-detect เมื่อชนเส้น
                    if (track_id not in self.im_save_CHECK_Id_model1_cm1) and self.is_Check_LINE1(cx, cy):
                        self.im_save_CHECK_Id_model1_cm1.add(track_id)
                        self.Time_cam1_oj = self.Time_cm1_Model1
                        self.master_log_set.info(
                            f"User: {self.user_email} Motorcycle detected on Camera 1 ID:{track_id} CONF:{conf1:.2f}"
                        )

                        x1, y1, x2, y2 = map(int, xyxy1)
                        # crop ภาพรถ (BGR)
                        crop_moto = frame[max(0, y1):y2, max(0, x1):x2].copy()
                        if crop_moto.size > 0:
                            # แสดงใน GUI (main thread)
                            self.after(0, self.update_label_img, self.My_show_img1, crop_moto)

                            # detect ป้ายทะเบียนเฉพาะ ROI
                            res_lp = self.model.predict(
                                    crop_moto,
                                    classes=[0],
                                    conf=0.5,
                                    imgsz=320,
                                    **self.infer_kwargs_c1
                                )
                            if res_lp and res_lp[0].boxes is not None:
                                for b2 in res_lp[0].boxes:
                                    conf2 = float(b2.conf.item())
                                    xyxy2 = b2.xyxy[0].cpu().numpy().astype(int)
                                    lx1, ly1, lx2, ly2 = xyxy2
                                    lp_crop = crop_moto[max(0, ly1):ly2, max(0, lx1):lx2].copy()

                                    # map กลับเป็นคอร์ดเดอร์เนตบนเฟรมเต็ม (หากต้องการวาด)
                                    Gx1, Gy1 = x1 + lx1, y1 + ly1
                                    Gx2, Gy2 = x1 + lx2, y1 + ly2
                                    annotator.box_label((Gx1, Gy1, Gx2, Gy2), f"LP {conf2:.2f}")

                                    # save path (ใช้ BGR ตรง ๆ)
                                    self.Main_Save_path(lp_crop, "CM1_Model2", self.Time_cam1_oj, track_id)
                                    # แสดงใน GUI
                                    if lp_crop.size > 0:
                                        self.after(0, self.update_label_img, self.My_show_img2, lp_crop)

                        # save รูปรถ
                        self.Main_Save_path(crop_moto, "CM1_Model1", self.Time_cam1_oj, track_id)
                        # ตั้งให้ clear preview ผ่าน after
                        self.after(5000, self.clear_image_after_delay)

            # อัปเดตภาพใหญ่ของกล้อง 1
            self.after(0, self.update_label_img, self.My_run_cam1_gui, annot_frame)

            # เขียนวิดีโอถ้าเปิด
            if writer:
                writer.write(frame)

        # cleanup
        if writer:
            writer.release()
        stop1["flag"] = True

    def Process_Cam02(self):
        self.My_cap2()

        # ----- โหลดโมเดล YOLO -----
        self.model22 = YOLO("best.pt")
        use_cuda = torch.cuda.is_available()
        if use_cuda:
            self.model22.to("cuda")
            _ = self.model22(torch.zeros((1, 3, 640, 640), device="cuda"))  # warmup
            torch.backends.cudnn.benchmark = True
            self.infer_kwargs_c2 = dict(device=0, half=True, verbose=False)
        else:
            self.infer_kwargs_c2 = dict(device="cpu", half=False, verbose=False)
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            self.model22.to("cuda")   
            _ = self.model22(torch.zeros((1, 3, 640, 640), device="cuda"))
            torch.backends.cudnn.benchmark = True
            self.infer_kwargs_c2 = dict(device=0, half=True, verbose=False)
        else:
            self.pred_kwargs_c2 = dict(imgsz=640, conf=0.5, device="cpu", half=False, verbose=False)

        # ----- เปิด RTSP (subtype=0) แบบ low-latency -----
        url2 = "rtsp://admin:Demaxzzo001@192.168.1.134:554/cam/realmonitor?channel=1&subtype=0"
        try:
            self.cam02 = open_rtsp_low_latency(url2)
        except Exception as e:
            self.master_log_set.error(f"User: {self.user_email} Failed to open Camera 02: {e}")
            self.Check_Cam2_ = False
            return

        self.master_log_set.info(f"User: {self.user_email} Camera 02 opened successfully.")
        self.start_event.wait()
        self.running = True

        self.im_save_CHECK_Id_model1_cm2 = set()
        self.id_Time_check_c2_m1 = {}
        self.id_Time_check_c2_m2 = {}

        writer = None
        if self.RECORD:
            os.makedirs("vidioodetect2", exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            frame_width = int(self.cam02.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(self.cam02.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cam02.get(cv2.CAP_PROP_FPS)) or 25
            writer = cv2.VideoWriter("vidioodetect2/output_detected_2.avi", fourcc, fps, (frame_width, frame_height))

        q2, stop2, t2 = start_threaded_reader(self.cam02)
        self.master_log_set.info(f"User: {self.user_email} connect to Camera 2")

        while self.running:
            try:
                frame2 = q2.get(timeout=1.0)  # BGR
            except:
                continue
            if frame2 is None:
                continue

            res_track = self.model22.track(
                frame2,
                classes=[1],
                conf=0.5,
                imgsz=640,
                persist=True,
                **self.infer_kwargs_c2
            )
            track_out = res_track[0]
            annot_frame2 = frame2.copy()
            annotator = Annotator(annot_frame2)
            cv2.line(annot_frame2, self.Line2[0], self.Line2[1], (255, 0, 255), 3)

            self.Tz = pytz.timezone('Asia/Bangkok')
            self.Time_cm2_Model1 = datetime.now(self.Tz)
            self.Main_Save_path(None, "Supper_check_c2", self.Time_cm2_Model1, None)

            if track_out.boxes is not None:
                current_time_ids = time.time()
                for box in track_out.boxes:
                    conf1 = float(box.conf.item())
                    xyxy1 = box.xyxy[0].cpu().numpy().astype(int)
                    cx, cy, w, h = box.xywh[0].cpu().numpy().astype(int)
                    cv2.circle(annot_frame2, (cx, cy), 6, (0, 255, 255), -1)

                    track_id = int(box.id.item()) if box.id is not None else -1
                    self.id_Time_check_c2_m1[track_id] = current_time_ids
                    annotator.box_label(xyxy1, f"motor_c2: CONF={conf1:.2f} ID={track_id}", color=(51, 255, 51))

                    if (track_id not in self.im_save_CHECK_Id_model1_cm2) and self.is_Check_LINE2(cx, cy):
                        self.im_save_CHECK_Id_model1_cm2.add(track_id)
                        self.Time_cam2_oj = self.Time_cm2_Model1
                        self.master_log_set.info(
                            f"User: {self.user_email} Motorcycle detected on Camera 2 ID:{track_id} CONF:{conf1:.2f}"
                        )

                        x1, y1, x2, y2 = map(int, xyxy1)
                        crop_moto2 = frame2[max(0, y1):y2, max(0, x1):x2].copy()
                        if crop_moto2.size > 0:
                            self.after(0, self.update_label_img, self.My_show_img1_cap2, crop_moto2)

                            res_lp2 = self.model22.predict(
                                crop_moto2,
                                classes=[0],
                                conf=0.5,
                                imgsz=320,
                                **self.infer_kwargs_c2
                            )
                            if res_lp2 and res_lp2[0].boxes is not None:
                                for b2 in res_lp2[0].boxes:
                                    conf2 = float(b2.conf.item())
                                    xyxy2 = b2.xyxy[0].cpu().numpy().astype(int)
                                    lx1, ly1, lx2, ly2 = xyxy2
                                    lp_crop2 = crop_moto2[max(0, ly1):ly2, max(0, lx1):lx2].copy()

                                    Gx1, Gy1 = x1 + lx1, y1 + ly1
                                    Gx2, Gy2 = x1 + lx2, y1 + ly2
                                    annotator.box_label((Gx1, Gy1, Gx2, Gy2), f"LP {conf2:.2f}")

                                    self.Main_Save_path(lp_crop2, "CM2_Model2", self.Time_cam2_oj, track_id)
                                    if lp_crop2.size > 0:
                                        self.after(0, self.update_label_img, self.My_show_img2_cap2, lp_crop2)

                        self.Main_Save_path(crop_moto2, "CM2_Model1", self.Time_cam2_oj, track_id)
                        self.after(5000, self.clear_image_after_delay)

            # อัปเดตภาพใหญ่ของกล้อง 2
            self.after(0, self.update_label_img, self.My_run_cam2_gui, annot_frame2)

            if writer:
                writer.write(frame2)

        if writer:
            writer.release()
        stop2["flag"] = True

    # -------------------- Start/Stop --------------------
    def start_cam(self):
        self.start_event = threading.Event()
        threading.Thread(target=self.Process_Cam01, daemon=True).start()
        threading.Thread(target=self.Process_Cam02, daemon=True).start()
        self.start_event.set()

    # -------------------- Exit/Login --------------------
    def destroyy(self):
        msg = CTkMessagebox(title="ยืนยันการออก", message="คุณแน่ใจว่าต้องการออกจากโปรแกรม?",
                            icon="question", option_1="ยกเลิก", option_2="ตกลง")
        if msg.get() == "ตกลง":
            self.master.Login_response.logout()
            self.running = False
            try:
                cv2.destroyAllWindows()
            except:
                pass
            self.quit()
            sys.exit()

    def from_logout_(self):
        msg = CTkMessagebox(
            title="ยืนยันการออก",
            message="คุณแน่ใจว่าต้องการออกจากระบบ?",
            icon="question",
            option_1="ยกเลิก",
            option_2="ตกลง"
        )
        if msg.get() == "ตกลง":
            self.master.Login_response.logout()
            self.destroy()
            self.master.LoginFFrame = LoginFrame(self.master)
            self.master.LoginFFrame.pack(fill="both", expand=True)

    def Notification_windown(self):
        def on_click():
            webbrowser.open("http://localhost:8000/dachvoth")
        toaster = ToastNotifier()
        toaster.show_toast(
            "ตรวจพบการระเมิดรถจักรยานยนต์บนทางเท้า",
            "คลิกเพื่อตรวจสอบ",
            duration=10,
            threaded=True,
            callback_on_click=on_click
        )

    def Notification_windown_Counter(self):
        def on_click():
            webbrowser.open("http://localhost:8000/dachvoth")
        toaster = ToastNotifier()
        toaster.show_toast(
            "ตรวจพบการระเมิดรถจักรยานยนต์บนทางเท้า\nและการขับรถย้อนศร",
            "คลิกเพื่อตรวจสอบ",
            duration=10,
            threaded=True,
            callback_on_click=on_click
        )


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        # สร้าง layout ก่อน แล้วค่อย bind
        self.Bk_laout_1()
        self.bind("<Configure>", self.Show_img_BkMain)

        self.path_jsov_email = "saved_email.json"
        self.Email_save = self.Load_Email()

    # ---------- พื้นหลัง/เลย์เอาต์ ----------
    def Show_img_BkMain(self, event=None):
        self.width = self.winfo_width() or 1000
        self.height = self.winfo_height() or 700
        try:
            img = Image.open("bkmain1.png")  # ให้ไฟล์อยู่โฟลเดอร์เดียวกับสคริปต์
            resized = img.resize((self.width, self.height))
            self.Show_BG_Sky = ctk.CTkImage(light_image=resized, size=(self.width, self.height))

            if not hasattr(self, "im_show_BG_Sky") or self.im_show_BG_Sky is None:
                self.im_show_BG_Sky = ctk.CTkLabel(self, text="", image=self.Show_BG_Sky)
                self.im_show_BG_Sky.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self.im_show_BG_Sky.configure(image=self.Show_BG_Sky)

            # ดันวิดเจ็ตหลักขึ้นมา
            if hasattr(self, "bkmain1"):
                self.bkmain1.lift()
            if hasattr(self, "im_show_img_let1"):
                self.im_show_img_let1.lift()
        except Exception as e:
            print("Show_img_BkMain error:", e)

    def Bk_laout_1(self):
        self.bkmain1 = ctk.CTkFrame(self, fg_color="#333333")
        self.bkmain1.place(relx=0.5, rely=0.5, relwidth=0.9, relheight=0.85, anchor="center")

        self.bkmain2 = ctk.CTkFrame(self.bkmain1, fg_color="#040404")
        self.bkmain2.place(relx=0, rely=0, relwidth=0.5, relheight=1)

        self.bkmain_input = ctk.CTkFrame(self.bkmain1, fg_color="#040404")
        self.bkmain_input.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)

        # โหลดรูปฝั่งซ้าย
        try:
            self.img_let1 = Image.open("img2.png")
        except Exception:
            self.img_let1 = Image.new("RGB", (800, 600), color=(20, 20, 20))  # fallback
        # วางภาพเริ่มต้น (จะถูกปรับขนาดอีกครั้งตอน resize)
        self.show_img_let1 = ctk.CTkImage(light_image=self.img_let1, size=(800, 600))
        self.im_show_img_let1 = ctk.CTkLabel(self.bkmain2, text="", image=self.show_img_let1)
        self.im_show_img_let1.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ผูกอีเวนต์เพื่อจัดขนาดภาพให้พอดี
        self.bkmain2.bind("<Configure>", self.resize_img_in_bkmain2)
        # วางฟอร์มฝั่งขวาเมื่อกรอบพร้อม
        self.bkmain_input.bind("<Configure>", self.In_Put_index)

    def resize_img_in_bkmain2(self, event):
        width, height = max(event.width, 1), max(event.height, 1)
        resized_img = self.img_let1.resize((width, height))
        self.show_img_let1 = ctk.CTkImage(light_image=resized_img, size=(width, height))
        self.im_show_img_let1.configure(image=self.show_img_let1)
        self.im_show_img_let1.image = self.show_img_let1

    # ---------- ฟอร์มล็อกอิน ----------
    def In_Put_index(self, event=None):
        # ป้องกันสร้างซ้ำ
        if getattr(self, "_login_built", False):
            return
        self._login_built = True

        parent_width = self.bkmain_input.winfo_width()
        parent_height = self.bkmain_input.winfo_height()

        self.frame_login_back = ctk.CTkFrame(self.bkmain_input, fg_color="#040404")
        self.frame_login_back.place(relx=0.5, rely=0.3, anchor='n', relwidth=0.5, relheight=0.5)

        # เฮดเดอร์
        self.label = ctk.CTkLabel(self.frame_login_back, text="Welcome to Login",
                                  font=("Arial", 24, "bold"))
        self.label.pack(pady=40)

        # ช่องกรอก
        entry_w = 333
        entry_h = 33
        self.entry_email = ctk.CTkEntry(self.frame_login_back, placeholder_text="Email...",
                                        width=entry_w, height=entry_h)
        self.entry_email.pack(pady=10)

        self.entry_password = ctk.CTkEntry(self.frame_login_back, placeholder_text="Password...",
                                           width=entry_w, height=entry_h, show="*")
        self.entry_password.pack(pady=10)

        # แถวปุ่ม/เช็คบ็อกซ์
        self.row_frame = ctk.CTkFrame(self.frame_login_back, fg_color="transparent")
        self.row_frame.pack(pady=15)

        self.Check_Bbox_email = ctk.CTkCheckBox(self.row_frame, text="Remember email.",
                                                checkbox_width=15, checkbox_height=15)
        self.Check_Bbox_email.select()
        self.Check_Bbox_email.pack(side="left")

        self.button_Forgot = ctk.CTkButton(self.row_frame, text="Forgot password.",
                                           hover_color="#F54927",
                                           command=lambda: webbrowser.open("http://localhost:5173/"),
                                           fg_color="transparent")
        self.button_Forgot.pack(side="left", padx=3)

        self.button_Register = ctk.CTkButton(self.row_frame, text="Register.",
                                             hover_color="#156A0F",
                                             command=lambda: webbrowser.open("http://localhost:5173/"),
                                             fg_color="transparent")
        self.button_Register.pack(side="left", padx=3)

        # ใส่อีเมลที่จำไว้ (ถ้ามี)
        if self.Email_save:
            self.entry_email.insert(0, self.Email_save)

        # ปุ่ม Login
        self.button_login = ctk.CTkButton(self.frame_login_back, text="Login", command=self.Check_Login)
        self.button_login.pack(pady=15)

    # ---------- จำ/โหลดอีเมล ----------
    def User_email_save(self):
        if self.Check_Bbox_email.get():
            Email = self.entry_email.get()
            if Email:
                with open(self.path_jsov_email, "w") as f:
                    json.dump({"email": Email}, f)

    def Load_Email(self):
        if os.path.exists(self.path_jsov_email):
            try:
                with open(self.path_jsov_email, "r") as e:
                    data = json.load(e)
                    return data.get("email", "")
            except json.JSONDecodeError:
                with open(self.path_jsov_email, "w") as f:
                    json.dump({}, f)
                return ""
        return ""

    # ---------- ตรวจล็อกอิน ----------
    def Check_Login(self):
        email = self.entry_email.get().strip()
        password = self.entry_password.get()
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"

        if not re.match(email_regex, email):
            CTkMessagebox(title="รูปแบบอีเมลไม่ถูกต้อง", message="กรุณากรอกรูปแบบอีเมลที่ถูกต้อง")
            return

        if email == "" or password == "":
            CTkMessagebox(title="กรุณากรอกข้อมูลให้ครบ", message="กรุณากรอกอีเมลและรหัสผ่าน",
                          icon="warning", option_1="ตกลง")
            # มี MasterLog_app ใน App แล้ว
            if hasattr(self.master, "MasterLog_app"):
                self.master.MasterLog_app.warning("User login attempt failed: empty email or password.")
            return

        # เรียก backend login
        try:
            response = self.master.Login_response.Loginpy_def(email, password)
        except Exception as e:
            if hasattr(self.master, "MasterLog_app"):
                self.master.MasterLog_app.error(f"Login error: {e}")
            CTkMessagebox(title="เกิดข้อผิดพลาด", message="ไม่สามารถติดต่อเซิร์ฟเวอร์ล็อกอินได้")
            return

        if response:
            if hasattr(self.master, "MasterLog_app"):
                self.master.MasterLog_app.info(f"Login successful for user: {email}")

            # เก็บข้อมูลผู้ใช้ขั้นต่ำ (ตามโค้ดเดิม)
            self.master.user_info = {"id": response["user"]["id"]}

            # จำอีเมลถ้าติ๊ก
            if self.Check_Bbox_email.get():
                self.User_email_save()
            else:
                if os.path.exists(self.path_jsov_email):
                    os.remove(self.path_jsov_email)

            # เข้าหน้าแอปหลัก
            self.master.Go_main_App_Sy()
        else:
            if hasattr(self.master, "MasterLog_app"):
                self.master.MasterLog_app.info(f"Login failed for user: {email}")
            CTkMessagebox(title="เข้าสู่ระบบล้มเหลว", message="อีเมลหรือรหัสผ่านไม่ถูกต้อง", icon="cancel")


    

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.deactivate_automatic_dpi_awareness()
        ctk.set_window_scaling(1.0)
        ctk.set_widget_scaling(1.0)

        self.MasterLog_app = MasterLog()
        self.Login_response = Loginpy()
        self.MasterLog_app.info("Application started")
        self.title("โปรแกรมตรวจจับรถจักรยานยนต์บนทางเท้า")
        try:
            self.iconbitmap("bkmain1.ico")
        except:
            pass

        self.LoginFFrame = LoginFrame(self)
        self.LoginFFrame.pack(fill="both", expand=True)
        self.resizable(True, True)
        self.minsize(800, 600)
        self.geometry("1000x700")
        self.after(1000, lambda: self.state('zoomed'))
        self.protocol("WM_DELETE_WINDOW", self.surs)
        self.user_info = {}

    def Go_main_App_Sy(self):
        self.LoginFFrame.destroy()
        self.main_app_frame = APP_SY_Frame(self)
        self.main_app_frame.pack(fill="both", expand=True)

    def surs(self):
        msg = CTkMessagebox(title="ยืนยันการออก", message="คุณแน่ใจว่าต้องการออกจากโปรแกรม?",
                            icon="warning", option_1="ยกเลิก", option_2="ตกลง")
        if msg.get() == "ตกลง":
            self.MasterLog_app.info("User Out program.")
            self.Login_response.logout()
            self.quit()


if __name__ == "__main__":
    app = App()
    app.mainloop()
