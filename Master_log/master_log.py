import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

class MasterLog:
    def __init__(self, base_log_dir="logs"):
        self.base_log_dir = base_log_dir
        self.logger = None
        self.setup_logger()

    def setup_logger(self):
        # วันที่ปัจจุบัน
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # โฟลเดอร์สำหรับวันนั้น
        dated_log_dir = os.path.join(self.base_log_dir, today_str)
        os.makedirs(dated_log_dir, exist_ok=True)  # สร้างโฟลเดอร์ถ้ายังไม่มี

        # ชื่อไฟล์ log
        log_file_path = os.path.join(dated_log_dir, "system.log")

        # สร้าง logger
        self.logger = logging.getLogger("MasterLogger")
        self.logger.setLevel(logging.INFO)

        # เช็คว่า handler ถูกเพิ่มไปแล้วหรือยัง
        if not self.logger.handlers:
            handler = TimedRotatingFileHandler(
                log_file_path, when="midnight", interval=1, backupCount=7, encoding="utf-8"
            )
            handler.suffix = "%Y-%m-%d"
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)


if __name__ == "__main__":
    log = MasterLog()
    log.info("เริ่มบันทึกข้อมูลระบบ")
    log.error("เกิดข้อผิดพลาดในการเชื่อมต่อกล้อง")
