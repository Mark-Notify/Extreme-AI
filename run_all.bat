@echo off
REM ไปที่โฟลเดอร์ไฟล์นี้ก่อน
cd /d "%~dp0"

REM เปิดหน้าต่างแรก รันบอท AI main.py
start "ExtremeAI main" cmd /k "python main.py"

REM เปิดหน้าต่างสอง รัน Dashboard (ปรับ port ได้ตามที่ใช้จริง)
start "ExtremeAI dashboard" cmd /k "uvicorn dashboard.server:app --host 127.0.0.1 --port 8000"
