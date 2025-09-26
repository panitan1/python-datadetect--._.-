import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from CTkMenuBar import *
from PIL import Image
import webbrowser
import numpy as np
import pytz
import cv2
import sys
import os
import threading
from ultralytics import YOLO 
from ultralytics.utils.plotting import Annotator
from datetime import datetime ,timedelta
import time
from ultralytics.utils import ThreadingLocked
from server_mysql.mysql_server import insert  , login_data
import uuid
from win10toast_click import ToastNotifier
from multiprocessing import Process



ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")

class APP_SY_Frame(ctk.CTkFrame):
    def __init__(self , master):
        super().__init__(master)
        self.master = master
        self.cam01 = cv2.VideoCapture("vidio\\test11.mp4")
        self.cam02 = cv2.VideoCapture("vidio\\test22.mp4")
        self.model = YOLO("yolov8x.pt").cuda()
        self.model_page = YOLO("gui\\best.pt").cuda()
        self.model22 = YOLO("yolov8x.pt").cuda()
        self.model_page22 = YOLO("gui\\best copy.pt").cuda()
        self.save_lock = threading.Lock()
        self.save_lock2 = threading.Lock()
        self.Time_CM1_MO1 = None  # เพิ่มตัวแปรสำหรับเก็บเวลา
        self.Time_CM2_MO1 = None  # เพิ่มตัวแปรสำหรับเก็บเวลา
        self.Time_CM1_MO2 = None  # เพิ่มตัวแปรสำหรับเก็บเวลา
        self.Time_CM2_MO2 = None  # เพิ่มตัวแปรสำหรับเก็บเวลา
        self.CM1_Model1_list = []  # เก็บภาพรถจาก Cam01
        self.CM2_Model1_list = []  # เก็บภาพรถจาก Cam02
        self.CM1_Model2_list = []
        self.CM2_Model2_list = []
        self.CM1_M1_M2_Path = []
        self.CM2_M1_M2_Path = []
        self.period = None
        self.Line1 =  np.array([[169, 771], [1343, 488]])
        self.Line2 = np.array([[1732, 834], [678, 545]])
        self.MuNuAPP_main()
        self.Main_CV2()
        # self.My_cap1()              # ✅ สร้าง self.My_run_cam1 ก่อน
        # self.My_cap2()
        self.My_show_ui_My_cap1()
        self.My_show_ui_My_cap2()
        self.start_cam()
        

        
    def MuNuAPP_main(self):
        self.munubar = CTkMenuBar(self)
        self.buttun01 = self.munubar.add_cascade("Munu")
        self.dropdown = CustomDropdownMenu(widget=self.buttun01)
        self.dropdown.add_option(option="Camela 1")
        self.dropdown.add_option(option="Camela 2")
        self.dropdown.add_separator() 
        self.dropdown.add_option(option="Folder " ,command= self.Folder)
        self.MuNuAPP_Profile_and_Dash()
    
    def Folder(self):
        path = "Save_detection"
        os.startfile(path)
    
    def MuNuAPP_Profile_and_Dash(self):
        self.buttun02 = self.munubar.add_cascade("Profile")
        self.dropdown2 = CustomDropdownMenu(widget=self.buttun02)
        self.dropdown2.add_option(option="Profile", command= lambda: webbrowser.open("http://localhost:5173/"))
        self.dropdown2.add_option(option="Dashboard" , command= lambda: webbrowser.open("http://localhost:5173/dashdata"))
        self.dropdown2.add_separator() 
        self.dropdown2.add_option(option="Logout" ,command=self.from_logout_)
        self.dropdown2.add_option(option="Exit" , command= self.destroyy)

  

    def Main_CV2(self):
        self.bkAPPmain = ctk.CTkFrame(self, fg_color="#686363"  )
        self.bkAPPmain.pack(fill="both", expand=True)
        
    def My_cap1(self):
        self.Ar_cm1_box = ctk.CTkFrame(self.bkAPPmain , fg_color="#000000")
        self.Ar_cm1_box.place(relx=0.003, rely=0.0018, relwidth=0.6, relheight=0.490)
        
        self.My_run_cam1_gui = ctk.CTkLabel(self.Ar_cm1_box ,text="")
        self.My_run_cam1_gui.pack(expand=True, fill="both")



    def My_cap2(self):
        self.Ar_cm2_box = ctk.CTkFrame(self.bkAPPmain , fg_color="#000000")
        self.Ar_cm2_box.place(relx=0.003, rely=0.5, relwidth=0.6, relheight=0.490)
        
        self.My_run_cam2_gui = ctk.CTkLabel(self.Ar_cm2_box ,text="")
        self.My_run_cam2_gui.pack(expand=True, fill="both")

    def My_show_ui_My_cap1(self):
        self.Main_Text_My_cap1 = ctk.CTkFrame(self.bkAPPmain , fg_color="#2C2C2C" )
        self.Main_Text_My_cap1.place(relx=0.604, rely=0.001, relwidth=0.393, relheight=0.07)
        
        self.TextMain_cap1 = ctk.CTkLabel(self.Main_Text_My_cap1 , text=f"กล้องหมายเลข 1")
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
        
        self.TextMain_cap2 = ctk.CTkLabel(self.Main_Text_My_cap2, text=f"กล้องหมายเลข 2")
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
        
        
    def My_time_tz(self):
        tz = pytz.timezone('Asia/Bangkok')
        now = datetime.now(tz)
        Time_Save_img = datetime.now(self.Tz).strftime("%H-%M-%S")
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

        save_dir = f"Save_detection/{year}/{month_str}/{today}/{period}/{Time_Save_img}"
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    @ThreadingLocked()   
    def Process_Cam01(self):
        self.My_cap1()
        self.start_event.wait()
        self.running = True
        
        self.im_SAVE_Id_model1_cm1 = set()
        self.im_save_CHECK_Id_model1_cm1 = set()
        
        self.im_SAVE_Id_model2_cm1 = set()
        self.im_save_CHECK_Id_model2_cm1 = set()
        
        self.id_Time_check_c1_m1 = {}
        self.id_Time_check_c1_m2 = {}
        
        while self.running and self.save_lock:
            
            ret, frame = self.cam01.read()
            if not ret:
                CTkMessagebox(title="Error", message=f"ไม่สามารถรับเชื่อมต่อกล้อง01ได้ \n {ret}", icon="cancel")
            
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            original_frame = frame.copy()
            cv2.line(frame, self.Line1[0], self.Line1[1], (255, 0, 255), 3)
            annotator = Annotator(frame)
            annotated_frame = annotator.result()
            
            
            runYOLOm1 = self.model.track(frame, classes=[3], conf=0.7, persist=True)
            annotated_frame1 = runYOLOm1[0]
        
            if annotated_frame1.boxes is not None:
                current_time_ids = time.time()
                current_frame_ids = set()  # ชุดสำหรับเก็บ ID ในเฟรมปัจจุบัน
                for box in annotated_frame1.boxes:
                    class_if_model1 = int(box.cls.item())
                    Conf_if_model1 = box.conf.item()
                    xyxy_if_model1 = box.xyxy[0]
                    cx, cy, w, h = box.xywh[0].cpu().numpy().astype(int)
                    cv2.circle(frame, (cx, cy), 10, (5, 123, 255), -1)
                    
                    if box.id is not None:
                        track_id = int(box.id.item())
                        current_frame_ids.add(track_id)  # เพิ่ม ID เข้าไปในชุดของเฟรมปัจจุบัน
                        self.id_Time_check_c1_m1[track_id] = current_time_ids
                 
                        annotator.box_label(xyxy_if_model1, label=f"model1: {class_if_model1} -- {Conf_if_model1:.2f} -- {int(track_id)}")
                  
                        
                        self.im_SAVE_Id_model1_cm1.add(track_id)
                        
                        if self.im_SAVE_Id_model1_cm1 != self.im_save_CHECK_Id_model1_cm1 and self.is_Check_LINE1(cx, cy, self.Line1[0], self.Line1[1]):
                            self.im_save_CHECK_Id_model1_cm1.update(self.im_SAVE_Id_model1_cm1)
                            self.Tz = pytz.timezone('Asia/Bangkok')
                            self.Time_cm1_Model1 = datetime.now(self.Tz)
                            x1, y1, x2, y2 = map(int, xyxy_if_model1)
             
                            
                            Crop_Img_c1_model_1 = original_frame[y1:y2, x1:x2]

                            print("💚")
                            self.Main_Save_path(Crop_Img_c1_model_1, "CM1_Model1",self.Time_cm1_Model1)
                            img = Image.fromarray(Crop_Img_c1_model_1)
                            label_width = self.My_show_img1.winfo_width()
                            label_height = self.My_show_img1.winfo_height()
                            resizeimg = img.resize((label_width, label_height))
                            imgSHOWCtkm1_c1 = ctk.CTkImage(light_image=resizeimg, size=(label_width, label_height))
                            self.My_show_img1.configure(image=imgSHOWCtkm1_c1)
                            self.My_show_img1.image = imgSHOWCtkm1_c1
                            # print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>{Crop_Img_c1_model_1}<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                            if Crop_Img_c1_model_1.size >= 1:
                                runYOLOm2 = self.model_page(Crop_Img_c1_model_1, classes=[0], conf = 0.5 )
                                annotated_frame2 = runYOLOm2[0]
                                
                                if annotated_frame2.boxes is not None:
                                    for box in annotated_frame2.boxes:
                                        class_if_model2 = int(box.cls.item())
                                        conf_if_model2 = box.conf.item()
                                        xyxy_if_model2 = box.xyxy[0]
                                            
                                        annotator.box_label(xyxy_if_model2 , label=f"model2 : {class_if_model2} -- {conf_if_model2:.2f}")
                                        self.Tz = pytz.timezone('Asia/Bangkok')
                                        self.Time_cm1_Model2 = datetime.now(self.Tz)
                                        x1 ,y1 , x2 ,y2 = map(int , xyxy_if_model2)
                                        Crop_Img_c1_model_2 = Crop_Img_c1_model_1[y1:y2 , x1:x2]
                                        self.Main_Save_path(Crop_Img_c1_model_2 , "CM1_Model2" , self.Time_cm1_Model2)
                                        
                                        img = Image.fromarray(Crop_Img_c1_model_2)
                                        label_width = self.My_show_img2.winfo_width()
                                        label_height = self.My_show_img2.winfo_height()
                                        resizeimg = img.resize((label_width ,label_height))
                                        imgSHOWCtkm2_c1 = ctk.CTkImage(light_image= resizeimg , size= (label_width ,label_height ))
                                        self.My_show_img2.configure(image = imgSHOWCtkm2_c1)
                                        self.My_show_img2.image = imgSHOWCtkm2_c1
                                            
                                else:
                                    pass
                            else:
                                pass
                        else:
                            pass


                missing_ids = self.im_SAVE_Id_model1_cm1 - current_frame_ids
                for lost_id in missing_ids:
                    if lost_id in self.id_Time_check_c1_m1:
                        time_since_last_seen = current_time_ids - self.id_Time_check_c1_m1[lost_id]
                        if time_since_last_seen > 10:
                            self.im_save_CHECK_Id_model1_cm1.discard(lost_id) 
                            self.im_SAVE_Id_model1_cm1.discard(lost_id)     
                            del self.id_Time_check_c1_m1[lost_id]             
                            # print(f"ตรวจสอบ ID {lost_id} | ล่าสุด: {self.id_Time_check_c1_m1[lost_id]} | ตอนนี้: {current_time_ids} | หายไปแล้ว {time_since_last_seen:.2f} วินาที")


                
                try: 
                    img1 = Image.fromarray(annotated_frame)
                    label_width = self.My_run_cam1_gui.winfo_width()
                    label_height = self.My_run_cam1_gui.winfo_height()
                    resiz_img = img1.resize((label_width, label_height))
                    imgTK = ctk.CTkImage(light_image=resiz_img, size=(label_width, label_height))
                
                    # อัปเดต GUI
                    self.My_run_cam1_gui.configure(image=imgTK)
                    self.My_run_cam1_gui.image = imgTK
                    
                    cv2.waitKey(1)
                except:
                    pass
        
                           
    @ThreadingLocked()
    def Process_Cam02(self):
        self.My_cap2()
        self.start_event.wait()
        self.running = True
        
        self.im_SAVE_Id_model1_cm2 = set()
        self.im_save_CHECK_Id_model1_cm2 = set()
        
        self.im_SAVE_Id_model2_cm2 = set()
        self.im_save_CHECK_Id_model2_cm2 = set()
        
        self.id_Time_check_c2_m1 = {}
        self.id_Time_check_c2_m2 = {}
        
        while self.running and self.save_lock2:
            
            ret, frame2 = self.cam02.read()
            if not ret:
                CTkMessagebox(title="Error", message=f"ไม่สามารถรับเชื่อมต่อกล้อง02ได้ \n {ret}", icon="cancel")
            
            frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
            original_frame = frame2.copy()
            cv2.line(frame2, self.Line2[0], self.Line2[1], (255, 0, 255), 3)
            annotator = Annotator(frame2)
            annotated_frame = annotator.result()
            
            runYOLOm1 = self.model22.track(frame2, classes=[3], conf=0.7, persist=True)
            annotated_frame1 = runYOLOm1[0]
            
            if annotated_frame1.boxes is not None:
                current_time_ids = time.time()
                current_frame_ids_C2_m1 = set()
                for box in annotated_frame1.boxes:
                    class_if_model1 = int(box.cls.item())
                    Conf_if_model1 = box.conf.item()
                    xyxy_if_model1 = box.xyxy[0]
                    cx, cy, w, h = box.xywh[0].cpu().numpy().astype(int)
                    cv2.circle(frame2, (cx, cy), 10, (5, 123, 255), -1)
                    
                    if box.id is not None:
                        track_id = int(box.id.item())
                        current_frame_ids_C2_m1.add(track_id)
                        self.id_Time_check_c2_m1[track_id] = current_time_ids
                        
                        annotator.box_label(xyxy_if_model1, label=f"model1: {class_if_model1} -- {Conf_if_model1:.2f} -- {int(track_id)}")
                        
                        self.im_SAVE_Id_model1_cm2.add(track_id)
                        
                        if self.im_SAVE_Id_model1_cm2 != self.im_save_CHECK_Id_model1_cm2 and self.is_Check_LINE2(cx, cy, self.Line2[0], self.Line2[1]):
                            self.im_save_CHECK_Id_model1_cm2.update(self.im_SAVE_Id_model1_cm2)
                            self.Tz = pytz.timezone('Asia/Bangkok')
                            self.Time_cm2_Model1 = datetime.now(self.Tz)
                            x1, y1, x2, y2 = map(int, xyxy_if_model1)
                            
                            Crop_Img_c2_model_1 = original_frame[y1:y2, x1:x2]
            
                            print("🩷")
                            self.Main_Save_path(Crop_Img_c2_model_1, "CM2_Model1", self.Time_cm2_Model1)
                            
                            img = Image.fromarray(Crop_Img_c2_model_1)
                            label_width = self.My_show_img1_cap2.winfo_width()
                            label_height = self.My_show_img1_cap2.winfo_height()
                            resizeimg = img.resize((label_width, label_height))
                            imgSHOWCtkm1_c2 = ctk.CTkImage(light_image=resizeimg, size=(label_width, label_height))
                            self.My_show_img1_cap2.configure(image=imgSHOWCtkm1_c2)
                            self.My_show_img1_cap2.image = imgSHOWCtkm1_c2
                            
                            if Crop_Img_c2_model_1.size >= 1:
                                runYOLOm2 = self.model_page22(Crop_Img_c2_model_1, classes=[0], conf=0.7)
                                annotated_frame2 = runYOLOm2[0]
                                
                                if annotated_frame2.boxes is not None:
                                    for box in annotated_frame2.boxes:
                                        class_if_model2 = int(box.cls.item())
                                        conf_if_model2 = box.conf.item()
                                        xyxy_if_model2 = box.xyxy[0]
                                        
                                        annotator.box_label(xyxy_if_model2, label=f"model2: {class_if_model2} -- {conf_if_model2:.2f}")
                                        self.Tz = pytz.timezone('Asia/Bangkok')
                                        self.Time_cm2_Model2 = datetime.now(self.Tz)
                                        x1, y1, x2, y2 = map(int, xyxy_if_model2)
                                        Crop_Img_c2_model_2 = Crop_Img_c2_model_1[y1:y2, x1:x2]
                                        self.Main_Save_path(Crop_Img_c2_model_2, "CM2_Model2", self.Time_cm2_Model2)
                                        
                                        img = Image.fromarray(Crop_Img_c2_model_2)
                                        label_width = self.My_show_img2_cap2.winfo_width()
                                        label_height = self.My_show_img2_cap2.winfo_height()
                                        resizeimg = img.resize((label_width, label_height))
                                        imgSHOWCtkm2_c2 = ctk.CTkImage(light_image=resizeimg, size=(label_width, label_height))
                                        self.My_show_img2_cap2.configure(image=imgSHOWCtkm2_c2)
                                        self.My_show_img2_cap2.image = imgSHOWCtkm2_c2
                                else:
                                    pass
                            else:
                                pass
                        else:
                            pass
                    
                missing_ids = self.im_SAVE_Id_model1_cm2 - current_frame_ids_C2_m1
                for lost_id in missing_ids:
                    if lost_id in self.id_Time_check_c2_m1:
                        time_since_last_seen = current_time_ids - self.id_Time_check_c2_m1[lost_id]
                        if time_since_last_seen > 10:
                            self.im_save_CHECK_Id_model1_cm2.discard(lost_id)
                            self.im_SAVE_Id_model1_cm2.discard(lost_id)
                            del self.id_Time_check_c2_m1[lost_id]
                
                try:
                    img2 = Image.fromarray(annotated_frame)
                    label_width = self.My_run_cam2_gui.winfo_width()
                    label_height = self.My_run_cam2_gui.winfo_height()
                    resiz_img = img2.resize((label_width, label_height))
                    imgTK2 = ctk.CTkImage(light_image=resiz_img, size=(label_width, label_height))
                    
                    self.My_run_cam2_gui.configure(image=imgTK2)
                    self.My_run_cam2_gui.image = imgTK2
                    
                    cv2.waitKey(1)
                except:
                    pass
                                        
    def point_line_distance(self, cx, cy, line_start, line_end):
        x0, y0 = cx, cy
        x1, y1 = line_start
        x2, y2 = line_end

        numerator = abs((y2 - y1)*x0 - (x2 - x1)*y0 + x2*y1 - y2*x1)
        denominator = ((y2 - y1)**2 + (x2 - x1)**2)**0.5
        distance = numerator / denominator
        return distance
    
    
                               
    def is_Check_LINE1(self, cx, cy , line_start ,line_end , tolerance=10):
        min_x ,max_x = min(line_start[0] , line_end[0]), max(line_start[0], line_end[0])
        min_y, max_y = min(line_start[1], line_end[1]), max(line_start[1], line_end[1])
        
        if not (min_x - tolerance <= cx <= max_x + tolerance and min_y - tolerance <= cy <= max_y + tolerance):
            return False


        distance = self.point_line_distance(cx, cy, line_start, line_end)

        return distance <= tolerance
    
    def is_Check_LINE2(self, cx, cy , line_start ,line_end , tolerance=10):
        min_x ,max_x = min(line_start[0] , line_end[0]), max(line_start[0], line_end[0])
        min_y, max_y = min(line_start[1], line_end[1]), max(line_start[1], line_end[1])
        
        if not (min_x - tolerance <= cx <= max_x + tolerance and min_y - tolerance <= cy <= max_y + tolerance):
            return False


        distance = self.point_line_distance(cx, cy, line_start, line_end)

        return distance <= tolerance


    def Main_Save_path(self, frame, ID_camala, timestamp):
        path = self.My_time_tz()
        unique_id = uuid.uuid4().hex[:6]
        # บันทึกข้อมูลลงลิสต์
        if ID_camala == "CM1_Model1":
            self.Time_CM1_MO1 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            self.CM1_Model1 = frame
            self.CM1_Model1_list.append({
                'image': self.CM1_Model1,
                'timestamp': self.Time_CM1_MO1
            })

        if ID_camala == "CM2_Model1":
            self.Time_CM2_MO1 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            self.CM2_Model1 = frame
            self.CM2_Model1_list.append({
                'image': self.CM2_Model1,
                'timestamp': self.Time_CM2_MO1
            })

        if ID_camala == "CM1_Model2":
            self.Time_CM1_MO2 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            self.CM1_Model2 = frame
            self.CM1_Model2_list.append({
                'image': self.CM1_Model2,
                'timestamp': self.Time_CM1_MO2
            })

        if ID_camala == "CM2_Model2":
            self.Time_CM2_MO2 = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            self.CM2_Model2 = frame
            self.CM2_Model2_list.append({
                'image': self.CM2_Model2,
                'timestamp': self.Time_CM2_MO2
            })

        # ตรวจสอบเวลาและบันทึก
        if self.Time_CM1_MO1 and self.Time_CM2_MO1:
            time1 = datetime.strptime(self.Time_CM1_MO1, '%Y-%m-%d %H:%M:%S')
            time2 = datetime.strptime(self.Time_CM2_MO1, '%Y-%m-%d %H:%M:%S')

            if abs(time1 - time2) <= timedelta(seconds=1):
                dateSQL = time1.strftime('%Y-%m-%d')
                timeSQL = time1.strftime('%H:%M:%S')

                for i, item in enumerate(self.CM1_Model1_list):
                    C1_M1_Path_SQL = f"{path}/_C1_Model1_{i}_{unique_id}.jpg"
                    if cv2.imwrite(C1_M1_Path_SQL, item['image']):
                        self.CM1_M1_M2_Path.append(C1_M1_Path_SQL)
                        print(f"Saved C1_Model1_{i}.jpg")

                for i, item in enumerate(self.CM2_Model1_list):
                    C2_M1_Path_SQL = f"{path}/_C2_Model1_{i}_{unique_id}.jpg"
                    if cv2.imwrite(C2_M1_Path_SQL, item['image']):
                        self.CM2_M1_M2_Path.append(C2_M1_Path_SQL)
                        print(f"Saved C2_Model1_{i}.jpg")


                for i, item in enumerate(self.CM1_Model2_list):
                    C1_M2_Path_SQL = f"{path}/_C_one_Model2_{i}_{unique_id}.jpg"
                    if cv2.imwrite(C1_M2_Path_SQL, item['image']):
                        self.CM1_M1_M2_Path.append(C1_M2_Path_SQL)
                        print(f"Saved C1_Model2_{i}.jpg")

                for i, item in enumerate(self.CM2_Model2_list):
                    C2_M2_Path_SQL = f"{path}/_C_two_Model2_{i}_{unique_id}.jpg"
                    if cv2.imwrite(C2_M2_Path_SQL, item['image']):
                        self.CM2_M1_M2_Path.append(C2_M2_Path_SQL)
                        print(f"Saved C2_Model2_{i}_{unique_id}.jpg")


                    
                insert(self.period, dateSQL, timeSQL, self.CM1_M1_M2_Path, self.CM2_M1_M2_Path)
                self.Notification_windown()
                    
            # ล้างลิสต์
            self.CM1_Model1_list = []
            self.CM2_Model1_list = []
            self.CM1_Model2_list = []
            self.CM2_Model2_list = []
    
    def start_cam(self):
        self.start_event = threading.Event()
        threading.Thread(target= self.Process_Cam01 , daemon=True).start()
        threading.Thread(target= self.Process_Cam02 , daemon=True).start()
        self.start_event.set()
    
        
    def destroyy(self):
        msg = CTkMessagebox(title="ยืนยันการออก", message="คุณแน่ใจว่าต้องการออกจากโปรแกรม?", 
                            icon="question", option_1="ยกเลิก", option_2="ตกลง")
        if msg.get() == "ตกลง":

            self.running = False
            self.cam01.release()
            self.cam02.release()
            cv2.destroyAllWindows()
            self.quit()
            sys.exit()
    
    def from_logout_(self):
        
        msg = CTkMessagebox(title="ยืนยันการออก", message="คุณแน่ใจว่าต้องการออกจากระบบ?", 
                            icon="question", option_1="ยกเลิก", option_2="ตกลง")
        if msg.get() == "ตกลง":
            try:
                self.cam01.release()
                self.cam02.release()
                self.after(100 , self.quit)
                cv2.destroyAllWindows()
                self.master.LoginFFrame = LoginFrame(self.master) 
                self.master.LoginFFrame.pack(fill="both", expand=True)
            except:
                pass

    


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



class LoginFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.bind("<Configure>", self.Show_img_BkMain)
        self.Bk_laout_1()
    def Show_img_BkMain(self, event=None):
        self.width = self.winfo_width()
        self.height = self.winfo_height()

        # โหลดภาพและปรับขนาด
        img = Image.open("gui\\bkmain1.png")
        resized = img.resize((self.width, self.height))
        self.Show_BG_Sky = ctk.CTkImage(light_image=resized, size=(self.width, self.height))
        self.im_show_BG_Sky = ctk.CTkLabel(self, text="", image=self.Show_BG_Sky)
        self.im_show_BG_Sky.place(x=0, y=0, relwidth=1, relheight=1)
        self.bkmain1.lift()
        self.im_show_img_let1.lift()

    def Bk_laout_1(self):
        self.bkmain1 = ctk.CTkFrame(self, fg_color="#333333")
        self.bkmain1.place(relx=0.5, rely=0.5, relwidth=0.9, relheight=0.85, anchor="center")

        self.bkmain2 = ctk.CTkFrame(self.bkmain1, fg_color="#040404")
        self.bkmain2.place(relx=0, rely=0, relwidth=0.5, relheight=1)

        self.bkmain_input = ctk.CTkFrame(self.bkmain1, fg_color="#040404")
        self.bkmain_input.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)


        self.img_let1 = Image.open("gui\\img2.png")
        self.im_show_img_let1 = ctk.CTkLabel(self.bkmain2, text="")
        self.im_show_img_let1.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.bkmain2.bind("<Configure>", self.resize_img_in_bkmain2)
        self.bkmain_input.bind("<Configure>" , self.In_Put_index)

    def resize_img_in_bkmain2(self, event):
        print(f"Event widget: {event.widget}, Width: {event.width}, Height: {event.height}")
        width = event.width
        height = event.height
        resized_img = self.img_let1.resize((width, height))
        self.show_img_let1 = ctk.CTkImage(light_image=resized_img, size=(width, height))
        self.im_show_img_let1.configure(image=self.show_img_let1)
        self.im_show_img_let1.image = self.show_img_let1


    def In_Put_index(self, event=None):
        print(f"Event widget: {event.widget}, Width: {event.width}, Height: {event.height}xxxxxxxxxxx")
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

        self.button_login = ctk.CTkButton(self.frame_login_back, text="Login", command=self.master.Go_main_App_Sy)


        self.button_login.pack(pady=20)
    
    
    def Check_Login(self):
        email = self.entry_email.get()
        password = self.entry_password.get()
        login_data(email, password)
        
        if login_data == True:
            self.master.Go_main_App_Sy()
        



class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("โปรแกรมตรวจจับมอไซบนทางเท้า")
        self.LoginFFrame = LoginFrame(self)
        self.LoginFFrame.pack(fill="both", expand=True)
        width = self.winfo_screenwidth() 
        height = self.winfo_screenheight()
        self.resizable(True, True)  # เปลี่ยนเป็น True เพื่อให้ยืดหยุ่น
        self.geometry(f"1000x700")  # ขนาดเริ่มต้น
        self.screen_app_width = self.winfo_screenwidth()
        self.after(1000, lambda: self.state('zoomed'))
        self.protocol("WM_DELETE_WINDOW", self.surs)


    def Go_main_App_Sy(self):
        self.LoginFFrame.destroy()
        self.main_app_frame = APP_SY_Frame(self)
        self.main_app_frame.pack(fill="both", expand=True)
        
        
    def surs(self):
        msg = CTkMessagebox(title="ยืนยันการออก", message="คุณแน่ใจว่าต้องการออกจากโปรแกรม?", 
                            icon="warning", option_1="ยกเลิก", option_2="ตกลง")
        
        if msg.get() == "ตกลง":
            self.quit()
            
            
        
if __name__ == "__main__":
    app = App()
    app.mainloop()
