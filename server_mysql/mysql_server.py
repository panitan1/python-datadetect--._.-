import json
import mysql.connector
import threading
import requests
from master_log.master_log import MasterLog

class datasql(MasterLog):
    def __init__(self):
        super().__init__()  # เรียก constructor ของ MasterLog
        self.lock = threading.Lock()
        self.mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="motorcycle_detection_system",
            connection_timeout=5,
            pool_size=5
        )
        self.info(f"Database connected: {self.mydb}")
        self.data_user = None

    def insert(self, period, Dete_detect, Time_detect, cm1_dt, cm2_dt):
        with self.lock:
            try:
                cursor = self.mydb.cursor()
                query = "INSERT INTO detections (Period, Dete_detect, Time_detect, cm1_dt, cm2_dt) VALUES (%s, %s, %s, %s, %s)"
                values = (period, Dete_detect, Time_detect, json.dumps(cm1_dt), json.dumps(cm2_dt))
                cursor.execute(query, values)
                self.mydb.commit()
                print("✅ Data inserted successfully")

            except mysql.connector.Error as err:
                self.error(f"Database error: {err}")

            finally:
                cursor.close()

class Loginpy(MasterLog):
    def __init__(self):
        super().__init__()
        self.Url = "http://localhost:3000/api/auth/login"
        self.lock = threading.Lock()
        self.data_user = None 
    def Loginpy_def(self, email, password):
        with self.lock:
            try:
                Set_data = {
                    "email": email,
                    "password": password,
                }
                response = requests.post(self.Url, json=Set_data)
                if response.status_code == 200:
                    self.data_user = response.json()
                    self.info(f"Login Successfully : {self.data_user}")
                    return self.data_user
                else:
                    self.error(f"Login fail ❌: {response.text}")
                    return None
            except Exception as e:
                self.error(f"❌ Error: {e}")
                return None
    
    def logout(self):
        if self.data_user is not None:
            self.info(f"Logout user: {self.data_user.get('user', {}).get('email', 'unknown')}")
        else:
            self.info("No user is currently logged in.")

        self.data_user = None
        print("Successfully logged out.")