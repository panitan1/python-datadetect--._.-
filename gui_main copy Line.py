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
from ultralytics import YOLO 
from ultralytics.utils.plotting import Annotator , Colors 
from datetime import datetime 
import time
from server_mysql.mysql_server import datasql ,Loginpy
from win10toast_click import ToastNotifier
from server_mysql.mysql_server import MasterLog
import re
import json
from queue import Queue
from collections import deque
import supervision as sv
# --- Performance toggles (ADD) ---
cv2.setUseOptimized(True)
cv2.setNumThreads(1)  # กัน CPU thread แย่งกันเกินไป

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")
ctk.deactivate_automatic_dpi_awareness()
ctk.set_window_scaling(1.0)
ctk.set_widget_scaling(1.0)


class FileReader:
    def __init__(self, cap, loop=False):
        self.cap = cap
        self.loop = loop

    def read(self, timeout=0.0):  # ให้ซิกเนเจอร์เหมือน RTSPReader
        if not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        if not ret:
            if self.loop:
                # กลับไปต้นไฟล์อัตโนมัติ (ถ้าต้องการเล่นวน)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            else:
                return False, None
        return ret, frame

    def stop(self):
        pass

class RTSPReader:
    def __init__(self, cap):
        self.cap = cap
        self.latest = deque(maxlen=1)
        self.running = True
        self.t = threading.Thread(target=self._loop, daemon=True)
        self.t.start()

    def _loop(self):
        while self.running:
            if not self.cap.isOpened():
                time.sleep(0.05)
                continue
            # ลดคิวเฟรมค้าง
            if not self.cap.grab():
                time.sleep(0.005)
                continue
            ok, frame = self.cap.retrieve()
            if ok and frame is not None:
                self.latest.append(frame)
            else:
                time.sleep(0.005)

    def read(self, timeout=0.5):
        """คืนค่า (ret, frame). ret=False เมื่อยังไม่มีเฟรมภายใน timeout"""
        t0 = time.time()
        while self.running and (time.time() - t0) < timeout:
            if self.latest:
                return True, self.latest[-1]
            time.sleep(0.005)
        return False, None

    def stop(self):
        self.running = False
        try:
            self.t.join(timeout=0.2)
        except:
            pass

    

class APP_SY_Frame(ctk.CTkFrame):
    def __init__(self , master):
        super().__init__(master)
        self.master = master          
        self.show_loading_popup()
        # ctk.set_widget_scaling(0.8)
        ctk.set_window_scaling(1.0)
        ctk.set_widget_scaling(1.0)
        ctk.deactivate_automatic_dpi_awareness()
        
        self.save_lock = threading.Lock()
        self.user_email = self.master.user_info
        self.Time_CM1_MO1 = None  # เพิ่มตัวแปรสำหรับเก็บเวลา
        self.Time_CM2_MO1 = None  # เพิ่มตัวแปรสำหรับเก็บเวลา
        self.Time_CM1_MO2 = None  # เพิ่มตัวแปรสำหรับเก็บเวลา
        self.Time_CM2_MO2 = None  # เพิ่มตัวแปรสำหรับเก็บเวลา
        self.CM1_Model1_list = []  # เก็บภาพรถจาก Cam01
        self.CM2_Model1_list = []  # เก็บภาพรถจาก Cam02
        self.CM1_Model2_list = []
        self.CM2_Model2_list = []
        self.CM1_M1_M2_Path = set()
        self.CM2_M1_M2_Path = set()
        self.CM1_M1_M2_Path_the_one = set()
        self.CM2_M1_M2_Path_the_one = set()
        self.period = None
        
        self.line1 = sv.LineZone(
            start=sv.Point(163, 679), 
            end=sv.Point(1672, 191)
        )
        self.line_annotator1 = sv.LineZoneAnnotator(thickness=2, text_thickness=1, text_scale=0.5
                                                    ,display_in_count = False , display_out_count= False)
        
        self.line2 = sv.LineZone(
            start=sv.Point(1695, 863), 
            end=sv.Point(416, 325)
        )
        self.line_annotator2 = sv.LineZoneAnnotator(thickness=2, text_thickness=1, text_scale=0.5
                                                    ,display_in_count = False , display_out_count= False)


        self.Check_Line = False

        self.MuNuAPP_main()
        self.Main_CV2()
        self.My_show_ui_My_cap1()
        self.My_show_ui_My_cap2()
        self.start_cam()
        
        
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
        
        
        self.queue_cam1 = Queue(maxsize=5)
        self.queue_cam2 = Queue(maxsize=5)
        self.My_checkOut_cm1 = {} 
        self.My_checkOut_cm2 = {} 
        self.db = datasql()
        self.master_log_set = MasterLog()
        self.last_frame_cam1 = None
        self.last_frame_cam2 = None
        
        self.Check_ID_CM1 = set()
        self.Check_ID_CM2 = set()

    def MuNuAPP_main(self):
        self.munubar = CTkMenuBar(self)
        self.buttun01 = self.munubar.add_cascade("Munu")
        self.dropdown = CustomDropdownMenu(widget=self.buttun01)
        self.dropdown.add_option(option="Camela 1" , command=lambda: self.save_snapshot("cam1"))
        self.dropdown.add_option(option="Camela 2", command=lambda: self.save_snapshot("cam2"))
        self.dropdown.add_option(option="polygonzone", command= lambda: webbrowser.open("https://polygonzone.roboflow.com"))
        self.dropdown.add_separator() 
        self.dropdown.add_option(option="Folder " ,command= self.Folder)
        self.MuNuAPP_Profile_and_Dash()
    
    def Folder(self):
        path = "Save_detection"
        os.startfile(path)
    
    def MuNuAPP_Profile_and_Dash(self):
        self.buttun02 = self.munubar.add_cascade("Profile")
        self.dropdown2 = CustomDropdownMenu(widget=self.buttun02)
        self.dropdown2.add_option(option="Dashboard" , command= lambda: webbrowser.open("http://localhost:5173/dashdata"))
        self.dropdown2.add_separator() 
        self.dropdown2.add_option(option="Logout" ,command=self.from_logout_)
        self.dropdown2.add_option(option="Exit" , command= self.destroyy)



    def Main_CV2(self):
        self.bkAPPmain = ctk.CTkFrame(self, fg_color="#3D2C48"  )
        self.bkAPPmain.pack(fill="both", expand=True)
        
    def My_cap1(self):
        self.Ar_cm1_box = ctk.CTkFrame(self.bkAPPmain , fg_color="#000000")
        self.Ar_cm1_box.place(relx=0.003, rely=0.0018, relwidth=0.6, relheight=0.490)
        
        self.My_run_cam1_gui = ctk.CTkLabel(self.Ar_cm1_box ,text=f"")
        self.My_run_cam1_gui.pack(expand=True, fill="both")



    def My_cap2(self):
        self.Ar_cm2_box = ctk.CTkFrame(self.bkAPPmain , fg_color="#000000")
        self.Ar_cm2_box.place(relx=0.003, rely=0.5, relwidth=0.6, relheight=0.490)
        
        self.My_run_cam2_gui = ctk.CTkLabel(self.Ar_cm2_box ,text=f"")
        self.My_run_cam2_gui.pack(expand=True, fill="both")

    def My_show_ui_My_cap1(self):
        self.Main_Text_My_cap1 = ctk.CTkFrame(self.bkAPPmain , fg_color="#2C2C2C" )
        self.Main_Text_My_cap1.place(relx=0.604, rely=0.001, relwidth=0.393, relheight=0.07)
        
        self.TextMain_cap1 = ctk.CTkLabel(self.Main_Text_My_cap1 , text=f"กล้องหมายเลข 1" , font=("TH Sarabun New", 24)  )
        self.TextMain_cap1.pack(expand=True, fill="both")
 
        
    def Show_img_cap1(self):
        self.box1 = ctk.CTkFrame(self.bkAPPmain , fg_color="#000000")
        self.box1.place(relx=0.604, rely=0.08, relwidth=0.2, relheight=0.41)
        
        self.My_show_img1 = ctk.CTkLabel(self.box1, text="")
        self.My_show_img1.pack(expand=True, fill="both")
        
        
        self.box2 = ctk.CTkFrame(self.bkAPPmain , fg_color="#000000")
        self.box2.place(relx=0.808, rely=0.08, relwidth=0.19, relheight=0.41)
        
        self.My_show_img2 = ctk.CTkLabel(self.box2, text="")
        self.My_show_img2.pack(expand=True, fill="both")
    
    def My_show_ui_My_cap2(self):
        self.Main_Text_My_cap2 = ctk.CTkFrame(self.bkAPPmain , fg_color="#2C2C2C" )
        self.Main_Text_My_cap2.place(relx=0.604, rely=0.5, relwidth=0.393, relheight=0.07)
        
        self.TextMain_cap2 = ctk.CTkLabel(self.Main_Text_My_cap2, text=f"กล้องหมายเลข 2" ,font=("TH Sarabun New", 24) )
        self.TextMain_cap2.pack(expand=True, fill="both")
        
        self.Show_img_cap1()
        self.Show_img_cap2()
    
    
    def Show_img_cap2(self):
        self.box1_cap2 = ctk.CTkFrame(self.bkAPPmain , fg_color="#000000")
        self.box1_cap2.place(relx=0.604, rely=0.58, relwidth=0.2, relheight=0.41)
        
        self.My_show_img1_cap2 = ctk.CTkLabel(self.box1_cap2, text="")
        self.My_show_img1_cap2.pack(expand=True, fill="both")
        
        self.box2_cap2 = ctk.CTkFrame(self.bkAPPmain , fg_color="#000000")
        self.box2_cap2.place(relx=0.808, rely=0.58, relwidth=0.19, relheight=0.41)
        
        self.My_show_img2_cap2 = ctk.CTkLabel(self.box2_cap2, text="")
        self.My_show_img2_cap2.pack(expand=True, fill="both")
       
    def Process_Cam01(self):
        # === เตรียมกล้อง/โมเดล แบบเดียวกับ Cam02 (ต่างแค่ตัวแปร/ไฟล์) ===
        self.My_cap1()
        self.model = YOLO("best2.pt").to(0)  # << ใช้โมเดลของกล้อง1 ตามเดิม

        self.cam01 = cv2.VideoCapture("vidio\\X1_D3.mp4")
        self.cam01.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        reader1 = FileReader(self.cam01)

        if not self.cam01.isOpened():
            self.master_log_set.error(f"User: {self.user_email} Failed to open Camera 01.")
            self.Check_Cam1_ = False
            return
        else:
            self.master_log_set.info(f"User: {self.user_email} Camera 01 opened successfully.")

        self.start_event.wait()
        self.running = True

        os.makedirs("vidioodetect1", exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        frame_width  = int(self.cam01.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cam01.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cam01.get(cv2.CAP_PROP_FPS)) or 30

        self.out1 = cv2.VideoWriter("vidioodetect1/output_detected_1.avi", fourcc, fps, (frame_width, frame_height))
        self.master_log_set.info(f"User: {self.user_email} connect to Camera 1")

        while self.running:
            ret, frame1 = reader1.read()
            if not ret or frame1 is None:
                self.ERRORCAM_pp001 = "กล้องหมายเลข 1 ไม่ทำงาน กรุณาตรวจสอบการเชื่อมต่อ {ret}"
                try:
                    CTkMessagebox(title="Error", message=f"กล้องหมายเลข 1 ไม่ทำงาน กรุณาตรวจสอบการเชื่อมต่อ \n {ret}", icon="cancel")
                except:
                    pass
                self.Check_Cam1_ = False
                self.master_log_set.error(f"User: {self.user_email} Failed to connect to Camera 1 {ret}")
                break  # << ให้จบลูปเหมือน Cam02

            # เขียนไฟล์วิดีโอต้นฉบับ (BGR)
            self.out1.write(frame1)

            # === ตรวจจับ/ติดตาม เหมือน Cam02 ===
            results_list = self.model.track(
                frame1,
                classes=[0, 1],       # 0=license plate, 1=motorcycle (ตามโมเดลคุณ)
                persist=True,
                device="cuda",
                imgsz=640
            )
            annotated = results_list[0]

            original_frame_bgr = frame1.copy()
            annotator = Annotator(frame1)

            # เวลา/เส้น/ระบบบันทึก เหมือน Cam02
            self.Tz = pytz.timezone('Asia/Bangkok')
            self.Time_cm1_Model1 = datetime.now(self.Tz)
            self.Main_Save_path(None, "Supper_check_c1", self.Time_cm1_Model1, None)

            frame1 = self.line_annotator1.annotate(frame1, self.line1)

            if annotated.boxes is not None:
                detections = sv.Detections.from_ultralytics(annotated)
                crossed_in, crossed_out = self.line1.trigger(detections)

                if detections.tracker_id is not None:
                    for box, tid in zip(annotated.boxes, detections.tracker_id):
                        if box.id is None:
                            continue

                        class_id = int(box.cls.item())
                        tracker_id = int(tid)
                        conf = float(box.conf.item())
                        xyxy = box.xyxy[0]

                        # วาดป้ายเหมือน Cam02
                        if class_id == 1:
                            annotator.box_label(
                                xyxy,
                                label=f"motorcycle_c1: CONF={conf:.2f} ID={tracker_id}",
                                color=(51, 255, 51),
                                txt_color=(252, 109, 47)
                            )
                        elif class_id == 0:
                            annotator.box_label(
                                xyxy,
                                label=f"license plate: CONF={conf:.2f} ID={tracker_id}",
                                color=(204, 237, 0),
                                txt_color=(255, 153, 255)
                            )

                        # เงื่อนไขบันทึก "ครั้งแรกที่ข้ามเส้น" เหมือน Cam02
                        if (tracker_id not in self.Check_ID_CM1) and (crossed_in.any() or crossed_out.any()):
                            self.Check_ID_CM1.add(tracker_id)
                            self.Time_cam1_oj = self.Time_cm1_Model1
                            self.master_log_set.info(
                                f"User: {self.user_email} Motorcycle/Plate detected on Camera 1 ID:{tracker_id} CONF:{conf:.2f}"
                            )

                            x1, y1, x2, y2 = map(int, xyxy)
                            crop1_bgr = original_frame_bgr[y1:y2, x1:x2]
           
                            if class_id == 1:
                                # Motorcycle -> CM1_Model1 + โชว์ My_show_img1 (ของ Cam1)
                                self.Main_Save_path(crop1_bgr, "CM1_Model1", self.Time_cam1_oj, tracker_id)
                                try:
                                    crop1_rgb = cv2.cvtColor(crop1_bgr, cv2.COLOR_BGR2RGB)
                                    img = Image.fromarray(crop1_rgb)
                                    lw, lh = self.My_show_img1.winfo_width(), self.My_show_img1.winfo_height()
                                    img = img.resize((lw, lh))
                                    imgSHOW = ctk.CTkImage(light_image=img, size=(lw, lh))
                                    self.My_show_img1.configure(image=imgSHOW)
                                    self.My_show_img1.image = imgSHOW
                                    self.after(5000, self.clear_image_after_delay)
                                except:
                                    pass

                            if class_id == 0:
                                # License plate -> CM1_Model2 + โชว์ My_show_img2 (ของ Cam1)
                                self.Main_Save_path(crop1_bgr, "CM1_Model2", self.Time_cam1_oj, tracker_id)
                                try:
                                    crop1_rgb = cv2.cvtColor(crop1_bgr, cv2.COLOR_BGR2RGB)
                                    img = Image.fromarray(crop1_rgb)
                                    lw, lh = self.My_show_img2.winfo_width(), self.My_show_img2.winfo_height()
                                    img = img.resize((lw, lh))
                                    imgSHOW = ctk.CTkImage(light_image=img, size=(lw, lh))
                                    self.My_show_img2.configure(image=imgSHOW)
                                    self.My_show_img2.image = imgSHOW
                                    self.after(5000, self.clear_image_after_delay)
                                except:
                                    pass

            # อัปเดตภาพลง GUI (BGR -> RGB) เหมือน Cam02
            try:
                img_rgb = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
                img1 = Image.fromarray(img_rgb)
                lw, lh = self.My_run_cam1_gui.winfo_width(), self.My_run_cam1_gui.winfo_height()
                img1 = img1.resize((lw, lh))
                imgTK = ImageTk.PhotoImage(image=img1)
                self.My_run_cam1_gui.configure(image=imgTK)
                self.My_run_cam1_gui.image = imgTK
            except:
                pass


                    
    def Process_Cam02(self): 
        self.My_cap2()
        self.model22 = YOLO("best.pt").to(0)

        self.cam02 = cv2.VideoCapture(
            "vidio\X2_D.mp4"
        )
        
        self.cam02.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        reader2 = FileReader(self.cam02)
        if not self.cam02.isOpened():
            self.master_log_set.error(f"User: {self.user_email} Failed to open Camera 02.")
            self.Check_Cam2_ = False
            return
        else:
            self.master_log_set.info(f"User: {self.user_email} Camera 02 opened successfully.")
            

        self.start_event.wait()
        self.running = True

        os.makedirs("vidioodetect2", exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        frame_width = int(self.cam02.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cam02.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cam02.get(cv2.CAP_PROP_FPS)) or 30
        
        self.out2 = cv2.VideoWriter(f"vidioodetect2/output_detected_2.avi", fourcc, fps, (frame_width, frame_height))
        self.master_log_set.info(f"User: {self.user_email} connect to Camera 2")  
        while self.running:
            ret, frame2 = reader2.read()
            if not ret or frame2 is None:
                self.ERRORCAM_pp002 = "กล้องหมายเลข 2 ไม่ทำงาน กรุณาตรวจสอบการเชื่อมต่อ {ret}"
                CTkMessagebox(title="Error", message=f"กล้องหมายเลข 2 ไม่ทำงาน กรุณาตรวจสอบการเชื่อมต่อ \n {ret}", icon="cancel")
                self.Check_Cam2_ = False
                self.master_log_set.error(f"User: {self.user_email} Failed to connect to Camera 2 {ret}")
                break

            self.out2.write(frame2)

            results_list = self.model22.track(frame2, classes=[0,1], persist=True, device="cuda", imgsz=640)
            annotated_frame1 = results_list[0]

            original_frame_bgr = frame2.copy()
            annotator = Annotator(frame2)

            self.Tz = pytz.timezone('Asia/Bangkok')
            self.Time_cm2_Model1 = datetime.now(self.Tz)
            self.Main_Save_path(None, "Supper_check_c2", self.Time_cm2_Model1, None)
            frame2 = self.line_annotator2.annotate(frame2, self.line2)
            
            if annotated_frame1.boxes is not None :
                detections = sv.Detections.from_ultralytics(annotated_frame1)
                crossed_in, crossed_out = self.line2.trigger(detections)


                if detections.tracker_id is not None:
                    for box, tid in zip(annotated_frame1.boxes, detections.tracker_id):
                        class_if_model1 = int(box.cls.item())
                        tracker_id = int(tid)
                        Conf_if_model1 = float(box.conf.item())
                        xyxy_if_model1 = box.xyxy[0]
 
                        if box.id is None:
                            continue
                        if class_if_model1 == 1:
                            annotator.box_label(
                                xyxy_if_model1,
                                label=f"motorcycle_c2: CONF={Conf_if_model1:.2f} ID={tracker_id}",
                                color=(51, 255, 51), txt_color=(252, 109, 47)
                            )
                        if class_if_model1 == 0:
                            annotator.box_label(
                            xyxy_if_model1,
                            label=f"license plate: CONF={Conf_if_model1:.2f} ID={tracker_id}",
                            color=(204, 237, 0), txt_color=(255, 153, 255)
                        )
                        

                        if (tracker_id not in self.Check_ID_CM2) and (crossed_in.any() or crossed_out.any()):
                            self.Check_ID_CM2.add(tracker_id)
                            self.Time_cam2_oj = self.Time_cm2_Model1 

                            x1, y1, x2, y2 = map(int, xyxy_if_model1)
                            crop2_bgr = original_frame_bgr[y1:y2, x1:x2]

                            if class_if_model1 == 1:
                                # รถ (Model1) → เซฟ CM2_Model1 + โชว์ที่ My_show_img1_cap2 (ของ Cam2)
                                self.Main_Save_path(crop2_bgr, "CM2_Model1", self.Time_cam2_oj, tracker_id)
                                try:
                                    crop2_rgb = cv2.cvtColor(crop2_bgr, cv2.COLOR_BGR2RGB)
                                    img = Image.fromarray(crop2_rgb)
                                    lw, lh = self.My_show_img1_cap2.winfo_width(), self.My_show_img1_cap2.winfo_height()
                                    img = img.resize((lw, lh))
                                    imgSHOW = ctk.CTkImage(light_image=img, size=(lw, lh))
                                    self.My_show_img1_cap2.configure(image=imgSHOW)
                                    self.My_show_img1_cap2.image = imgSHOW
                                    self.after(5000, self.clear_image_after_delay)
                                except:
                                    pass

                            if class_if_model1 == 0:
     
                                self.Main_Save_path(crop2_bgr, "CM2_Model2", self.Time_cam2_oj, tracker_id)
                                try:
                                    crop2_rgb = cv2.cvtColor(crop2_bgr, cv2.COLOR_BGR2RGB)
                                    img = Image.fromarray(crop2_rgb)
                                    lw, lh = self.My_show_img2_cap2.winfo_width(), self.My_show_img2_cap2.winfo_height()
                                    img = img.resize((lw, lh))
                                    imgSHOW = ctk.CTkImage(light_image=img, size=(lw, lh))
                                    self.My_show_img2_cap2.configure(image=imgSHOW)
                                    self.My_show_img2_cap2.image = imgSHOW
                                    self.after(5000, self.clear_image_after_delay)
                                except:
                                    pass
                                       
            # ✅ อัปเดตภาพลง GUI หลัก (BGR -> RGB เฉพาะตอนแสดง)
            try:
                img_rgb = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
                img1 = Image.fromarray(img_rgb)
                lw, lh = self.My_run_cam2_gui.winfo_width(), self.My_run_cam2_gui.winfo_height()
                img1 = img1.resize((lw, lh))
                imgTK = ImageTk.PhotoImage(image=img1)
                self.My_run_cam2_gui.configure(image=imgTK)
                self.My_run_cam2_gui.image = imgTK
            except:
                pass                                

    def clear_image_after_delay(self):
        self.My_show_img1_cap2.configure(image="", text="")
        self.My_show_img1_cap2.image = None
        self.My_show_img1_cap2.update()
        self.My_show_img1.configure(image="", text="")
        self.My_show_img1.image = None
        

        self.My_show_img2_cap2.configure(image="", text="")
        self.My_show_img2_cap2.image = None
        self.My_show_img2_cap2.update()
        self.My_show_img2.configure(image = "", text="")
        self.My_show_img2.image = None
        # ล้างภาพจาก CTkLabel
        self.My_show_img1.configure(image="")
        self.My_show_img1.image = None
        # ล้างตัวแปรภาพ
        self.imgSHOWCtkm1_c1 = None
        self.imgSHOWCtkm1_c2 = None
        
        self.Crop_Img_c1_model_1 = None
        
    def show_loading_popup(self):
        CTkMessagebox(title="Info", message="กำลังโหลดข้อมูลกล้อง กรุณารอสักครู่",icon="check")


    def Main_Save_path(self, frame, ID_camala, timestamp, track_id):
        with self.save_lock:
            re_list_index_cm1_model1 = []
            re_list_index_cm2_model1 = []
            re_list_index_model2_c1 = []
            re_list_index_model2_c2 = []
            re_supprt_index1 = []
            re_supprt_index2 = []
            re_supprt_index1_model2 = []
            re_supprt_index2_model2 = []

            is_saved = False  # ตัวแปรควบคุมการทำงาน

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

            # ==== ADD: ค่าหน่วงและ helper ====
            FIRST_MODEL_GRACE = getattr(self, "FIRST_MODEL_GRACE", 1.5)  # หน่วง 1–2s สำหรับโมเดลแรก
            SINGLE_CAM_GRACE  = getattr(self, "SINGLE_CAM_GRACE", 2.0)   # ยืดหยุ่นเคส single-cam

            def _to_aware(ts_str: str):
                return tz.localize(datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S"))

            def _newest_time_in(lst):
                if not lst:
                    return None
                return max(_to_aware(item["timestamp"]) for item in lst)
            # ===================================

            if ID_camala == "CM1_Model1":
                self.Time_CM1_MO1 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.CM1_Model1 = frame
                self.Track_idC1M1 = track_id
                self.CM1_Model1_list.append({
                    'image': self.CM1_Model1,
                    'timestamp': self.Time_CM1_MO1,
                })

            if ID_camala == "CM2_Model1":
                self.Time_CM2_MO1 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.CM2_Model1 = frame
                self.Track_idC2M1 = track_id
                self.CM2_Model1_list.append({
                    'image': self.CM2_Model1,
                    'timestamp': self.Time_CM2_MO1,
                })
            print(self.CM2_Model1_list, "♡(ﾐ ᵕ̣̣̣̣̣̣ ﻌ ᵕ̣̣̣̣̣̣ ﾐ)ﾉ")

            if ID_camala == "CM1_Model2":
                self.Time_CM1_MO2 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.CM1_Model2 = frame
                self.Track_idC1M2 = track_id
                self.CM1_Model2_list.append({
                    'image': self.CM1_Model2,
                    'timestamp': self.Time_CM1_MO2,
                })

            if ID_camala == "CM2_Model2":
                self.Time_CM2_MO2 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.CM2_Model2 = frame
                self.Track_idC2M2 = track_id
                self.CM2_Model2_list.append({
                    'image': self.CM2_Model2,
                    'timestamp': self.Time_CM2_MO2,
                })

            if ID_camala == "Supper_check_c1":
                self.Supper_check_c1 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.Supper_check_c1_List = [{
                    'timestamp': self.Supper_check_c1,
                }]

            if ID_camala == "Supper_check_c2":
                self.Supper_check_c2 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.Supper_check_c2_List = [{
                    'timestamp': self.Supper_check_c2,
                }]

            # ==== ADD: หน่วงก่อนเข้า logic จับคู่/บันทึก เพื่อรออีกกล้อง ====
            if self.CM1_Model1_list or self.CM2_Model1_list:
                newest_c1 = _newest_time_in(self.CM1_Model1_list)
                newest_c2 = _newest_time_in(self.CM2_Model1_list)
                newest_any = max([dt for dt in [newest_c1, newest_c2] if dt is not None], default=None)
                if newest_any is not None:
                    if (now - newest_any).total_seconds() < FIRST_MODEL_GRACE:
                        # เพิ่งมีภาพจากโมเดลแรกเข้า รออีกนิดให้มีโอกาส match
                        return
            # ============================================================

            # ส่วนที่ 1: ตรวจจับ Matched detection จากทั้ง 2 กล้อง
            if self.CM1_Model1_list and self.CM2_Model1_list:

                for i, (item1, item2) in enumerate(zip(self.CM1_Model1_list, self.CM2_Model1_list)):
                    time_str1 = item1['timestamp']
                    time_str2 = item2['timestamp']

                    time_obj1 = datetime.strptime(time_str1, '%Y-%m-%d %H:%M:%S')
                    time_obj2 = datetime.strptime(time_str2, '%Y-%m-%d %H:%M:%S')

                    time_diff = abs((time_obj1 - time_obj2).total_seconds())

                    if time_diff <= 4:
                        self.master_log_set.info(f"User: {self.user_email} Matched detection from Camera 1 and Camera 2")

                        if time_obj1 < time_obj2:
                            time_to_use = time_obj1
                        else:
                            time_to_use = time_obj2

                        dateSQL = time_to_use.strftime('%Y-%m-%d')
                        timeSQL = time_to_use.strftime('%H:%M:%S')
                        timePATH = time_to_use.strftime('%H-%M-%S')
                        full_save_dir = f"{save_dir}/{timePATH}"
                        os.makedirs(full_save_dir, exist_ok=True)

                        for i_cm1, item in enumerate(self.CM1_Model1_list):
                            C1_M1_Path_SQL = f"{full_save_dir}/_C1_Model1_{i_cm1}.png"
                            if cv2.imwrite(C1_M1_Path_SQL, item['image']):
                                self.CM1_M1_M2_Path.add(C1_M1_Path_SQL)
                                self.master_log_set.info(f"User: {self.user_email} Save C1_Model1_{i_cm1}.png from Matched detection from Camera 1 and Camera 2")
                                print(f"บันทึก C1_Model1_{i_cm1}.png")
                            re_list_index_cm1_model1.append(i_cm1)

                        for i_cm2, item in enumerate(self.CM2_Model1_list):
                            C2_M1_Path_SQL = f"{full_save_dir}/_C2_Model1_{i_cm2}.png"
                            if cv2.imwrite(C2_M1_Path_SQL, item['image']):
                                self.CM2_M1_M2_Path.add(C2_M1_Path_SQL)
                                self.master_log_set.info(f"User: {self.user_email} Save C2_Model1_{i_cm2}.png from Matched detection from Camera 1 and Camera 2")
                                print(f"บันทึก C2_Model1_{i_cm2}.png")
                            re_list_index_cm2_model1.append(i_cm2)

                        for i_m2c1, item in enumerate(self.CM1_Model2_list):
                            print(self.CM1_Model2_list, "₍^⸝⸝> ·̫ <⸝⸝ ^₎")
                            C1_M2_Path_SQL = f"{full_save_dir}/_C_one_Model2_{i_m2c1}.png"
                            if cv2.imwrite(C1_M2_Path_SQL, item['image']):
                                self.CM1_M1_M2_Path.add(C1_M2_Path_SQL)
                                self.master_log_set.info(f"User: {self.user_email} Save C1_Model2_{i_m2c1}.png from Matched detection from Camera 1 and Camera 2")
                                print(f"บันทึก C1_Model2_{i_m2c1}.png")
                            re_list_index_model2_c1.append(i_m2c1)

                        for i_m2c2, item in enumerate(self.CM2_Model2_list):
                            C2_M2_Path_SQL = f"{full_save_dir}/_C_two_Model2_{i_m2c2}.png"
                            if cv2.imwrite(C2_M2_Path_SQL, item['image']):
                                self.CM2_M1_M2_Path.add(C2_M2_Path_SQL)
                                self.master_log_set.info(f"User: {self.user_email} Save C2_Model2_{i_m2c2}.png from Matched detection from Camera 1 and Camera 2")
                                print(f"บันทึก C2_Model2_{i_m2c2}.png")
                            re_list_index_model2_c2.append(i_m2c2)

                        if self.CM1_M1_M2_Path and self.CM2_M1_M2_Path:
                            cm1_out = sorted(map(str, self.CM1_M1_M2_Path))
                            cm2_out = sorted(map(str, self.CM2_M1_M2_Path))
                            self.db.insert(self.period, dateSQL, timeSQL, cm1_out, cm2_out)
                            self.Notification_windown()

                            for i in reversed(re_list_index_cm1_model1):
                                if i < len(self.CM1_Model1_list):
                                    del self.CM1_Model1_list[i]
                            for i in reversed(re_list_index_cm2_model1):
                                if i < len(self.CM2_Model1_list):
                                    del self.CM2_Model1_list[i]
                            for i in reversed(re_list_index_model2_c1):
                                if i < len(self.CM1_Model2_list):
                                    del self.CM1_Model2_list[i]
                            for i in reversed(re_list_index_model2_c2):
                                if i < len(self.CM2_Model2_list):
                                    del self.CM2_Model2_list[i]

                            self.master_log_set.info(f"User: {self.user_email} Matched detection from Camera 1 and Camera 2. Data saved successfully")
                            self.CM1_M1_M2_Path.clear()
                            self.CM2_M1_M2_Path.clear()
                            is_saved = True
                            return  # ออกจากฟังก์ชันทันทีหลังจากบันทึกเสร็จ

            # ส่วนที่ 2: ตรวจจับ Matched detection จากกล้อง 1 เท่านั้น
            if not is_saved and self.CM1_Model1_list and not self.CM2_Model1_list:
                for i, item1 in enumerate(self.CM1_Model1_list):
                    re_supprt_index1.append(i)

                    timeput = item1['timestamp']
                    Time_only_Cam1 = _to_aware(timeput)
                    age_sec = (now - Time_only_Cam1).total_seconds()

                    # ==== CHANGE: ใช้คงที่ SINGLE_CAM_GRACE ====
                    if age_sec < SINGLE_CAM_GRACE:
                        continue

                    # ตรวจสอบกับ Supper_check_c2_List ว่ามีข้อมูลเข้ามาหรือไม่
                    if not self.Supper_check_c2_List or abs((_to_aware(self.Supper_check_c2_List[0]['timestamp']) - Time_only_Cam1).total_seconds()) > 4:
                        self.master_log_set.info("Matched detection from Camera 1 only.")
                        print("บันทึกข้อมูลกล้อง 1 อิสระ")
                        timePATH = Time_only_Cam1.strftime('%H-%M-%S')
                        dateSQL = Time_only_Cam1.strftime('%Y-%m-%d')
                        timeSQL = Time_only_Cam1.strftime('%H:%M:%S')
                        full_save_dir = f"{save_dir}/{timePATH}"
                        os.makedirs(full_save_dir, exist_ok=True)

                        C1_M1_Path_SQL = f"{full_save_dir}/_C1_Model1_{i}.png"
                        if cv2.imwrite(C1_M1_Path_SQL, item1['image']):
                            self.CM1_M1_M2_Path_the_one.add(C1_M1_Path_SQL)
                            self.master_log_set.info(f"User: {self.user_email} Save C1_Model1_{i}.png from Matched detection from Camera 1 ")
                            print(f"บันทึก C1_Model1_{i}.png")

                        for j, item in enumerate(self.CM1_Model2_list):
                            C1_M2_Path_SQL = f"{full_save_dir}/_C_one_Model2_{j}.png"
                            if cv2.imwrite(C1_M2_Path_SQL, item['image']):
                                self.CM1_M1_M2_Path_the_one.add(C1_M2_Path_SQL)
                                self.master_log_set.info(f"User: {self.user_email} Save C1_Model2_{i}.png from Matched detection from Camera 1 ")
                                print(f"บันทึก C1_Model2_{j}.png")
                            re_supprt_index1_model2.append(j)

                        self.master_log_set.info(f"User: {self.user_email} detection from Camera 1 only. Data saved successfully")
                        cm1_out = sorted(map(str, self.CM1_M1_M2_Path_the_one))
                        self.db.insert(self.period, dateSQL, timeSQL, cm1_out, None)
                        self.Notification_windown()
                        self.CM1_M1_M2_Path_the_one.clear

                        if self.CM1_Model1_list:
                            for i in reversed(re_supprt_index1):
                                if i < len(self.CM1_Model1_list):
                                    del self.CM1_Model1_list[i]
                        if self.CM1_Model2_list:
                            for i in reversed(re_supprt_index1_model2):
                                if i < len(self.CM1_Model2_list):
                                    del self.CM1_Model2_list[i]
                        self.CM1_M1_M2_Path_the_one.clear()
                        is_saved = True
                        return  # ออกจากฟังก์ชันทันที

            # ส่วนที่ 3: ตรวจจับ Matched detection จากกล้อง 2 เท่านั้น
            if not is_saved and self.CM2_Model1_list and not self.CM1_Model1_list:
                for i, item1 in enumerate(self.CM2_Model1_list):
                    re_supprt_index2.append(i)

                    timeput = item1['timestamp']
                    Time_only_Cam2 = _to_aware(timeput)
                    age_sec = (now - Time_only_Cam2).total_seconds()

                    # ==== CHANGE: ใช้คงที่ SINGLE_CAM_GRACE ====
                    if age_sec < SINGLE_CAM_GRACE:
                        continue

                    if not self.Supper_check_c1_List or abs((_to_aware(self.Supper_check_c1_List[0]['timestamp']) - Time_only_Cam2).total_seconds()) > 4:
                        self.master_log_set.info(f"User: {self.user_email} Matched detection from Camera 2 only.")
                        timePATH = Time_only_Cam2.strftime('%H-%M-%S')
                        dateSQL = Time_only_Cam2.strftime('%Y-%m-%d')
                        timeSQL = Time_only_Cam2.strftime('%H:%M:%S')
                        full_save_dir = f"{save_dir}/{timePATH}"
                        os.makedirs(full_save_dir, exist_ok=True)

                        C2_M1_Path_SQL = f"{full_save_dir}/_C2_Model1_{i}.png"
                        if cv2.imwrite(C2_M1_Path_SQL, item1['image']):
                            self.CM2_M1_M2_Path_the_one.add(C2_M1_Path_SQL)
                            self.master_log_set.info(f"User: {self.user_email} Save C2_Model1_{i}.png from Matched detection from Camera 2")
                            print(f"บันทึก C2_Model1_{i}.png")

                        for j, item in enumerate(self.CM2_Model2_list):
                            C2_M2_Path_SQL = f"{full_save_dir}/_C_two_Model2_{j}.png"
                            if cv2.imwrite(C2_M2_Path_SQL, item['image']):
                                self.CM2_M1_M2_Path_the_one.add(C2_M2_Path_SQL)
                                self.master_log_set.info(f"User: {self.user_email} Save C2_Model2_{j}.png from Matched detection from Camera 2")
                                print(f"บันทึก C2_Model2_{j}.png")
                            re_supprt_index2_model2.append(j)

                        self.master_log_set.info(f"User: {self.user_email} detection from Camera 2 only. Data saved successfully")
                        cm2_out = sorted(map(str, self.CM2_M1_M2_Path_the_one))
                        self.db.insert(self.period, dateSQL, timeSQL, None, cm2_out)
                        self.Notification_windown()

                        self.Time_cam2_oj = None

                        if self.CM2_Model1_list:
                            for i in reversed(re_supprt_index2):
                                if i < len(self.CM2_Model1_list):
                                    del self.CM2_Model1_list[i]
                        if self.CM2_Model2_list:
                            for i in reversed(re_supprt_index2_model2):
                                if i < len(self.CM2_Model2_list):
                                    del self.CM2_Model2_list[i]
                        self.CM2_M1_M2_Path_the_one.clear()
                        is_saved = True
                        return  # ออกจากฟังก์ชันทันที

                    
    def start_cam(self):
        self.start_event = threading.Event()
        threading.Thread(target= self.Process_Cam01 , daemon=True).start()
        threading.Thread(target= self.Process_Cam02 , daemon=True).start()
        self.start_event.set()
    
        
    def destroyy(self):
        msg = CTkMessagebox(title="ยืนยันการออก", message="คุณแน่ใจว่าต้องการออกจากโปรแกรม?", 
                            icon="question", option_1="ยกเลิก", option_2="ตกลง")
        if msg.get() == "ตกลง":
            self.master.Login_response.logout()
            self.running = False
            cv2.destroyAllWindows()
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

            # ทำลายหน้า Main app แล้วกลับไป Login
            self.destroy()
            self.master.LoginFFrame = LoginFrame(self.master)
            self.master.LoginFFrame.pack(fill="both", expand=True)

    def Notification_windown(self):
        def on_click():
            webbrowser.open("http://localhost:8000/dachvoth")

        toaster = ToastNotifier()
        toaster.show_toast(
            "ตรวจพบการระเมิดรถจักยานยนต์บนทางเท้า",
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
            "ตรวจพบการระเมิดรถจักยานยนต์บนทางเท้า\nและการขับรถย้อนศร",
            "คลิกเพื่อตรวจสอบ",
            duration=10,
            threaded=True,
            callback_on_click=on_click
        )

    def save_snapshot(self, cam: str = "cam1"):
            ts = datetime.now(pytz.timezone('Asia/Bangkok')).strftime("%Y-%m-%d_%H-%M-%S")
            out_dir = os.path.join("Snapshots", datetime.now().strftime("%Y-%m-%d"))
            os.makedirs(out_dir, exist_ok=True)

            # แก้ไขบรรทัดนี้: เปลี่ยน self.snapshot_lock เป็น self.save_lock
            with self.save_lock: 
                if cam == "cam1":
                    frame_rgb = self.last_frame_cam1
                    cam_tag = "cam1"
                else:
                    frame_rgb = self.last_frame_cam2
                    cam_tag = "cam2"

                if frame_rgb is None:
                    CTkMessagebox(title="ยังไม่มีภาพ",
                                message=f"ยังไม่มีเฟรมล่าสุดจาก {cam_tag} หรือกล้องยังไม่พร้อม",
                                icon="warning")
                    return

                # cv2.imwrite คาดหวัง BGR -> ต้องแปลงกลับก่อน
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                out_path = os.path.join(out_dir, f"{ts}_{cam_tag}.png")

                ok = cv2.imwrite(out_path, frame_bgr)

            if ok:
                CTkMessagebox(title="บันทึกแล้ว ✅",
                            message=f"เซฟรูปเรียบร้อย:\n{out_path}",
                            icon="check")
            else:
                CTkMessagebox(title="บันทึกไม่สำเร็จ ❌",
                            message="ไม่สามารถบันทึกรูปได้",
                            icon="cancel")
        

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.bind("<Configure>", self.Show_img_BkMain)
        self.Bk_laout_1()
        self.path_jsov_email = "saved_email.json"
        self.Email_save = self.Load_Email()
        
        
    def Show_img_BkMain(self, event=None):
        self.width = self.winfo_width()
        self.height = self.winfo_height()

        # โหลดภาพและปรับขนาด
        img = Image.open("bkmain1.png")
        resized = img.resize((self.width, self.height))
        self.Show_BG_Sky = ctk.CTkImage(light_image=resized, size=(self.width, self.height))
        self.im_show_BG_Sky = ctk.CTkLabel(self, text="", image=self.Show_BG_Sky)
        self.im_show_BG_Sky.place(x=0, y=0, relwidth=1, relheight=1)
        self.bkmain1.lift()
        self.im_show_img_let1.lift()

    def Bk_laout_1(self):
        self.bkmain1 = ctk.CTkFrame(self, fg_color="#333333")
        self.bkmain1.place(relx=0.5, rely=0.5, relwidth=0.9, relheight=0.85, anchor="center")
        self.width = self.winfo_width()
        self.height = self.winfo_height()
        self.bkmain2 = ctk.CTkFrame(self.bkmain1, fg_color="#040404")
        self.bkmain2.place(relx=0, rely=0, relwidth=0.5, relheight=1)

        self.bkmain_input = ctk.CTkFrame(self.bkmain1, fg_color="#040404")
        self.bkmain_input.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)


        self.img_let1 = Image.open("img2.png")
        resized = self.img_let1.resize((self.width, self.height))
        self.Show_img_let1 = ctk.CTkImage(light_image=resized, size=(self.width, self.height))
        self.im_show_img_let1 = ctk.CTkLabel(self.bkmain2, text="", image=self.Show_img_let1 )
        self.im_show_img_let1.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.bkmain2.bind("<Configure>", self.resize_img_in_bkmain2)
        self.bkmain_input.bind("<Configure>" , self.In_Put_index)

    def resize_img_in_bkmain2(self, event):
        width = event.width
        height = event.height
        resized_img = self.img_let1.resize((width, height))
        self.show_img_let1 = ctk.CTkImage(light_image=resized_img, size=(width, height))
        self.im_show_img_let1.configure(image=self.show_img_let1)
        self.im_show_img_let1.image = self.show_img_let1


    def In_Put_index(self, event=None):
   
        if len(self.bkmain_input.winfo_children()) > 0:
            return  
        parent_width = self.bkmain_input.winfo_width() 
        parent_height = self.bkmain_input.winfo_height() 
        
        self.frame_login_back = ctk.CTkFrame(self.bkmain_input , fg_color="#040404")
        self.frame_login_back.place(relx=0.5, rely=0.3, anchor='n', relwidth=0.5, relheight=0.5)
        if parent_height >= 516 or parent_height >= 440:
            parent_width = 333
            parent_height = 33

        self.label = ctk.CTkLabel(self.frame_login_back, text="Welcome to Login" , width=parent_width , height=parent_height ,font=("Arial", 24, "bold"))
        self.label.pack(pady=40)

        self.entry_email = ctk.CTkEntry(self.frame_login_back, placeholder_text="Email...", width=parent_width, height=parent_height)
        self.entry_email.pack(pady=10)

        self.entry_password = ctk.CTkEntry(self.frame_login_back, placeholder_text="Password...", width=parent_width, height=parent_height, show="*")
        self.entry_password.pack(pady=10)
        
        self.row_frame = ctk.CTkFrame(self.frame_login_back, fg_color="transparent")
        self.row_frame.pack(pady=15)

        if self.Email_save:
            self.entry_email.insert(0, self.Email_save)
        # Checkbox
        self.Check_Bbox_email = ctk.CTkCheckBox(
            self.row_frame,
            text="Remember email.",
            checkbox_width=15,
            checkbox_height=15,
            
  

        )
        self.Check_Bbox_email.select()
        self.Check_Bbox_email.pack(side="left")  

        # ปุ่ม Forgot password
        self.button_Forgot = ctk.CTkButton(
            self.row_frame,
            text="Forgot password.",
            hover_color="#F54927", command= lambda: webbrowser.open("http://localhost:5173/"),
            fg_color="transparent", 
        )
        self.button_Forgot.pack(side="left", padx=3)
        
         # ปุ่ม Forgot password
        self.button_Forgot = ctk.CTkButton(
            self.row_frame,
            text="Register.",
            hover_color="#156A0F"
            , command= lambda: webbrowser.open("http://localhost:5173/"),
            fg_color="transparent", 
            
        )
        self.button_Forgot.pack(side="left" , padx=3)

        
        self.button_login = ctk.CTkButton(self.frame_login_back, text="Login", command=self.Check_Login)
        self.button_login.pack(pady=15)
    
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
                # ลบหรือเขียนใหม่ถ้าข้อมูลเสีย
                with open(self.path_jsov_email, "w") as f:
                    json.dump({}, f)
                return ""
        return ""

    def Check_Login(self):
        email = self.entry_email.get()
        password = self.entry_password.get()
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        
        check_email =  re.match(email_regex , email)
        if not check_email:
            CTkMessagebox(title="รูปแบบอีเมลไม่ถูกต้อง", message="กรุณากรอกรูปแบบอีเมลที่ถูกต้อง")
            return 
        if email == "" or password == "":
            CTkMessagebox(
                title="กรุณากรอกข้อมูลให้ครบ",
                message="กรุณากรอกอีเมลและรหัสผ่าน",
                icon="warning",
                option_1="ตกลง"
            )
            self.master.MasterLog_app.warning("User login attempt failed: email or password is empty.")
            return
        response = self.master.Login_response.Loginpy_def(email, password)
        if response:
            self.master.MasterLog_app.info(f"Login successful for user: {email}")
            self.master.user_info = {
                "id": response["user"]["id"],
                # "email": response["user"]["email"],
                # "type": response["user"]["userType"]
            }
            print("UserDetails Login:", response)
            if self.Check_Bbox_email.get():
                self.User_email_save()

            else:
                if os.path.exists(self.path_jsov_email):
                    os.remove(self.path_jsov_email)
            self.master.Go_main_App_Sy()
        else:
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
        self.iconbitmap("bkmain1.ico")
        self.LoginFFrame = LoginFrame(self)
        self.LoginFFrame.pack(fill="both", expand=True)
        width = self.winfo_screenwidth() 
        height = self.winfo_screenheight()
        self.resizable(True, True)  # เปลี่ยนเป็น True เพื่อให้ยืดหยุ่น
        self.minsize(800, 600)
        self.geometry(f"1000x700")  # ขนาดเริ่มต้น
        self.screen_app_width = self.winfo_screenwidth()
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
            self.MasterLog_app.info(f"User Out program.")
            self.Login_response.logout()
            self.quit()
            
            
        
if __name__ == "__main__":
    
    app = App()
    app.mainloop()
    
