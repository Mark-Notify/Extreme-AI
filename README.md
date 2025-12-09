# Extreme AI Bot Trade v4 (XAUUSD, MT5, WebSocket, Rule-based + LSTM)

โครงโปรเจกต์ **Extreme AI v4** ตามสเปกที่ให้มา (เน้น XAUUSD / ทองคำ) พร้อมโครงครบชุด:

1. วิเคราะห์ตลาด XAUUSD แบบ Realtime จาก MT5
2. Indicators ครบชุด: RSI, MACD, ATR, ADX, Regime (trending/sideways/reversal)
3. AI Engine:
   - Rule-based AI (Fallback ถ้าไม่มีโมเดล)
   - LSTM Deep Learning (ไฟล์ `models/extreme_lstm.keras`)
4. สร้างสัญญาณ PRE / CONFIRM พร้อมคำนวณ AI Probability
5. Auto Trading ผ่าน MT5 (ฟังก์ชัน `execute_order()` ใน `core/mt5_trader.py`)
6. Dashboard Web Realtime + WebSocket
7. สร้างกราฟ Chart แนบใน Discord
8. Log AI (`logs/ai_log.jsonl`) สำหรับ Train LSTM
9. Script เทรน AI: `python -m scripts.train_ai`
10. Discord Notifications + High Stability Mode

> โปรเจกต์นี้เป็น **Skeleton / Template**: โครงสร้าง + Logic หลักพร้อม stub ให้เอาไปต่อยอดใส่ API จริง, ปรับ Risk, และเพิ่ม Condition ได้เอง

---

## โครงสร้างโฟลเดอร์

```text
extreme_ai_v4_full/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ main.py                    # loop หลัก Extreme AI v4
├─ core/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ data_feed.py            # ดึงข้อมูลจาก MT5
│  ├─ indicators.py           # RSI / MACD / ATR / ADX
│  ├─ regime.py               # Regime Detection
│  ├─ rule_based.py           # Rule-based AI
│  ├─ lstm_model.py           # LSTM Model (PyTorch) + บันทึกเป็น .keras
│  ├─ ai_engine.py            # รวม Rule-based + LSTM เป็น Extreme AI
│  ├─ ai_logger.py            # บันทึก logs/ai_log.jsonl, last_state.json
│  ├─ charting.py             # วาดกราฟ + save png ใน /charts
│  ├─ mt5_trader.py           # execute_order() เชื่อม MT5 (ตอนนี้เป็น stub)
│  ├─ discord_notifier.py     # ส่งสัญญาณเข้า Discord
│  └─ stability.py            # helper ป้องกัน error ล่ม
├─ dashboard/
│  ├─ server.py               # FastAPI + WebSocket Dashboard
│  ├─ templates/
│  │  └─ index.html
│  └─ static/
│     ├─ app.js
│     └─ style.css
├─ scripts/
│  └─ train_ai.py             # python -m scripts.train_ai
├─ charts/                    # เก็บรูปสัญญาณ
└─ logs/                      # logs/ai_log.jsonl + last_state.json
```

---

## การติดตั้ง

```bash
pip install -r requirements.txt
```

สร้างไฟล์ `.env` จาก `.env.example`:

```bash
cp .env.example .env
```

ปรับค่า:
- MT5_SERVER / MT5_LOGIN / MT5_PASSWORD
- DISCORD_WEBHOOK_URL
- LOOP_INTERVAL_SEC (เช่น 5 วินาที)
- AUTO_TRADE_ENABLED = true/false

---

## การรันระบบ

### 1) รัน Dashboard + WebSocket

```bash
uvicorn dashboard.server:app --reload
```

เปิดเว็บ: http://localhost:8000

### 2) รัน Extreme AI Bot Loop

```bash
python main.py
```

บอทจะ:

- ดึงราคา XAUUSD จาก MT5
- คำนวณ Indicators + Regime
- เรียก AI Engine → AI Probability + Signal
- สร้าง PRE/CONFIRM Signal + Chart + Discord
- เขียน Log ลง `logs/ai_log.jsonl` และ `logs/last_state.json` สำหรับ Dashboard / AI

---

## การเทรน LSTM (Extreme AI)

เมื่อได้ log สักระยะ (ai_log.jsonl มีข้อมูลเยอะพอ), รัน:

```bash
python -m scripts.train_ai
```

สคริปต์จะ:

- โหลด `logs/ai_log.jsonl`
- เตรียม feature matrix + label
- เทรน LSTM
- เซฟโมเดลเป็น `models/extreme_lstm.keras`
- อัปเดต status ใน console

หลังเทรนเสร็จ รอบถัดไปใน `main.py` AI จะสลับไปใช้ LSTM อัตโนมัติ (ถ้าโหลดโมเดลสำเร็จ)

---

## หมายเหตุสำคัญ

- MT5: ต้องติดตั้ง MetaTrader 5 + เปิดบัญชี (Demo ก็ได้) แล้วกรอกข้อมูลใน `.env`
- ตอนนี้ `mt5_trader.py` เป็น stub: มีตัวอย่าง connect/login + execute_order symbol XAUUSD (แก้เพิ่มเติมได้)
- โปรเจกต์นี้เน้นเป็นโครง Extreme AI v4 ให้ต่อยอดเองได้ง่ายที่สุด
- **ไม่ควรใช้เทรดเงินจริงทันที** ควร Backtest + Forward test ให้มั่นใจก่อน
