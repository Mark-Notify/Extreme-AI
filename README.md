# 🤖 Extreme AI v4 — XAUUSD Gold Trading Bot

**Extreme AI v4** เป็นระบบเทรดทองคำ (XAUUSD) แบบอัตโนมัติด้วย AI เต็มรูปแบบ  
รองรับ MetaTrader 5 (MT5) · Rule-based AI · LSTM Deep Learning · GPT / Gemini LLM Advisor

> ⚠️ **คำเตือน**: การเทรดมีความเสี่ยง ควร Backtest และ Forward test บัญชี Demo ก่อนใช้เงินจริงเสมอ

---

## 📋 สารบัญ

1. [ความสามารถ (Features)](#-ความสามารถ-features)
2. [สถาปัตยกรรม AI](#-สถาปัตยกรรม-ai)
3. [โครงสร้างโฟลเดอร์](#-โครงสร้างโฟลเดอร์)
4. [การติดตั้ง](#-การติดตั้ง)
5. [การตั้งค่า .env](#️-การตั้งค่า-env)
6. [Quick Start สำหรับทุน 10,000 บาท/USD](#-quick-start-สำหรับทุน-10000-บาทusd)
7. [การรันระบบ](#-การรันระบบ)
8. [AI Signal Logic](#-ai-signal-logic)
9. [Risk Management](#-risk-management)
10. [LLM Advisor (GPT + Gemini)](#-llm-advisor-gpt--gemini)
11. [การเทรน LSTM](#-การเทรน-lstm)
12. [Dashboard Web](#-dashboard-web)
13. [Discord Notifications](#-discord-notifications)
14. [การปรับแต่ง AI Mode](#-การปรับแต่ง-ai-mode)
15. [Troubleshooting](#-troubleshooting)

---

## ✨ ความสามารถ (Features)

| Feature | รายละเอียด |
|---------|-----------|
| 📊 **8+ Indicators** | RSI, MACD, ATR, ADX, EMA(9/21/50), Bollinger Bands, Stochastic, Volume MA |
| 🕯️ **Candlestick Patterns** | Bullish/Bearish Engulfing, Hammer, Shooting Star, Doji |
| 🧠 **Dual AI Engine** | Rule-based (8 factors) + LSTM Deep Learning |
| 🤖 **LLM Advisor** | GPT-4o-mini + Gemini 1.5-flash ยืนยันสัญญาณ |
| 📐 **Dynamic SL/TP** | คำนวณ SL/TP อัตโนมัติตาม ATR + Regime + ADX + BB |
| 💰 **Dynamic Sizing** | Position sizing ตาม ATR risk-based + Kelly Criterion |
| 🛡️ **Drawdown Protection** | ลด lot อัตโนมัติเมื่อ drawdown > 5-10% |
| 🏛️ **Market Regime** | ตรวจ trending / sideways / reversal / volatile |
| ⏰ **Session Filter** | เทรดเฉพาะ London/NY session (Liquidity สูง) |
| 📱 **Discord Alerts** | แจ้งเตือน PRE/CONFIRM signal + Chart |
| 🖥️ **Web Dashboard** | Real-time dashboard ผ่าน WebSocket |
| 📈 **AI Evaluation** | วัด accuracy และ win rate จาก log จริง |

---

## 🧠 สถาปัตยกรรม AI

```
Raw OHLCV Data (MT5)
        │
        ▼
  Indicators Engine
  ├─ RSI(14)           ← Momentum oversold/overbought
  ├─ MACD(12,26,9)     ← Trend + crossover
  ├─ ATR(14)           ← Volatility → SL/TP sizing
  ├─ ADX(14)           ← Trend strength filter
  ├─ EMA(9/21/50)      ← Trend alignment (3-layer)
  ├─ Bollinger(20,2σ)  ← Volatility bands + squeeze
  ├─ Stochastic(14,3)  ← Oversold/overbought crossover
  ├─ Volume MA(20)     ← Volume confirmation
  └─ Candlestick       ← Engulfing / Hammer / Shooting Star
        │
        ▼
  ┌─────────────────────────────────┐
  │         AI Engine               │
  │  Rule-based (8 factors)  30%   │
  │  +                             │
  │  LSTM Deep Learning      70%   │
  │  (60-bar sequences)            │
  └─────────────────────────────────┘
        │ prob_up / prob_down / confidence
        ▼
  Market Regime Detection
  (trending / sideways / reversal / volatile)
        │
        ▼
  Signal Generator
  ├─ PRE Signal  (≥2 of 5 factors)
  └─ CONFIRM Signal (prob + confidence + min factors)
        │
        ▼ (optional)
  LLM Advisor
  ├─ GPT-4o-mini  → BUY/SELL/HOLD + reasoning
  └─ Gemini 1.5   → BUY/SELL/HOLD + reasoning
        │ consensus
        ▼
  Dynamic Position Sizing
  (ATR-based + Kelly Criterion + Drawdown Protection)
        │
        ▼
  Execute Order (MT5)
  SL = ATR × 1.5–2.2 (by regime)
  TP = SL × 1.4–2.5  (by regime + confidence)
```

---

## 📁 โครงสร้างโฟลเดอร์

```text
Extreme-AI/
├─ README.md
├─ requirements.txt
├─ .env.example              ← template สำหรับ config
├─ main.py                   ← loop หลัก Extreme AI v4
├─ run_all.py                ← รัน bot + dashboard พร้อมกัน
├─ core/
│  ├─ config.py              ← Settings ทั้งหมด (จาก .env)
│  ├─ data_feed.py           ← ดึงข้อมูลจาก MT5
│  ├─ indicators.py          ← RSI/MACD/ATR/ADX/EMA/BB/Stoch/Volume/Patterns
│  ├─ regime.py              ← Market Regime Detection
│  ├─ rule_based.py          ← Rule-based AI (8 factors)
│  ├─ lstm_model.py          ← LSTM Model (PyTorch)
│  ├─ ai_engine.py           ← รวม Rule-based + LSTM
│  ├─ ai_logger.py           ← บันทึก logs/ai_log.jsonl
│  ├─ charting.py            ← วาดกราฟ + save png
│  ├─ mt5_trader.py          ← execute_order() เชื่อม MT5
│  ├─ position_sizing.py     ← Dynamic position sizing + Kelly
│  ├─ trade_utils.py         ← Dynamic SL/TP calculation
│  ├─ llm_advisor.py         ← GPT + Gemini advisor
│  ├─ discord_notifier.py    ← Discord webhook
│  └─ stability.py           ← Error protection
├─ dashboard/
│  ├─ server.py              ← FastAPI + WebSocket
│  └─ templates/ + static/
├─ scripts/
│  ├─ train_ai.py            ← Train LSTM model
│  └─ backtest.py            ← Backtest AI
├─ models/                   ← extreme_lstm.keras (หลัง train)
└─ logs/                     ← ai_log.jsonl + last_state.json
```

---

## 🚀 การติดตั้ง

### ขั้นตอนที่ 1: ติดตั้ง Python dependencies

```bash
pip install -r requirements.txt
```

### ขั้นตอนที่ 2: ติดตั้ง MetaTrader 5

1. ดาวน์โหลด [MetaTrader 5](https://www.metatrader5.com/en/download)
2. สมัครบัญชี Demo กับโบรกเกอร์ที่รองรับ (Exness, ICMarkets, XM ฯลฯ)
3. เปิดบัญชี และจดชื่อ Server / Login / Password

### ขั้นตอนที่ 3: สร้างไฟล์ .env

```bash
cp .env.example .env
```

แก้ไขค่าใน `.env`:

```env
MT5_SERVER=Exness-MT5Trial17    # ชื่อ server โบรก
MT5_LOGIN=12345678              # หมายเลขบัญชี
MT5_PASSWORD=yourpassword       # รหัสผ่าน
```

---

## ⚙️ การตั้งค่า .env

### การตั้งค่าพื้นฐาน

| Key | ค่าแนะนำ | อธิบาย |
|-----|---------|--------|
| `SYMBOL` | `XAUUSDm` | สัญลักษณ์ทอง (ตรวจสอบชื่อจากโบรกของคุณ) |
| `TIMEFRAME` | `M1` | M1=1นาที, M5=5นาที, M15=15นาที |
| `LOOP_INTERVAL_SEC` | `1` | วิเคราะห์ทุก N วินาที |
| `AI_MODE` | `NORMAL` | SAFE/NORMAL/AGGRESSIVE |
| `LOOKBACK_BARS` | `500` | จำนวนแท่งย้อนหลังสำหรับ live loop |
| `TRAIN_BARS` | `5000` | จำนวนแท่งสำหรับเทรน LSTM (ดึงจาก MT5) |

### การตั้งค่า Risk Management

| Key | ค่าแนะนำ (10K) | อธิบาย |
|-----|---------------|--------|
| `RISK_PER_TRADE` | `0.01` | 1% ต่อไม้ (เสี่ยง 100 บาท/USD ต่อไม้) |
| `MAX_OPEN_TRADES` | `2` | สูงสุด 2 ไม้พร้อมกัน |
| `ATR_SL_MULTIPLIER` | `1.5` | SL ห่าง 1.5x ATR |
| `MIN_VOLUME` | `0.01` | 0.01 lot = ขั้นต่ำ |
| `MAX_VOLUME` | `1.0` | สูงสุด 1 lot (ทุน 10K) |
| `INITIAL_BALANCE` | `10000` | ทุนตั้งต้น (สำหรับ drawdown protection) |

### Signal Quality

| Key | ค่าแนะนำ | อธิบาย |
|-----|---------|--------|
| `MIN_CONFIRM_FACTORS` | `2` | ต้องผ่าน 2 filter ขึ้นไป |
| `AI_CONFIRM_PROB_UP_THRESHOLD` | `0.55` | ความมั่นใจ AI ขั้นต่ำ |
| `AI_AMPLIFY_FACTOR` | `3.0` | ขยายความต่างของสัญญาณ |

---

## 💰 Quick Start สำหรับทุน 10,000 บาท/USD

> เป้าหมาย: เทรดได้กำไรสม่ำเสมอด้วยทุน 10,000

### แนวคิดหลัก

- **เสี่ยง 1% ต่อไม้** = 100 บาท/USD ต่อการเทรด
- **RR ratio ≥ 1:2** = ชนะ 1 ครั้งคุ้มค่ากับแพ้ 2 ครั้ง
- **Win rate ≥ 45%** พร้อม RR 1:2 = ระยะยาวกำไร
- **Max 2 ไม้พร้อมกัน** = expose สูงสุด 2% = 200 บาท/USD

### ตั้งค่า .env สำหรับทุน 10K

```env
# ── ทุน & Risk ──
INITIAL_BALANCE=10000
RISK_PER_TRADE=0.01          # 1% = 100 บาท/USD ต่อไม้
MAX_OPEN_TRADES=2            # เปิดได้ 2 ไม้พร้อมกัน

# ── Signal Quality (เข้าไม้เฉพาะสัญญาณดี) ──
AI_MODE=NORMAL
MIN_CONFIRM_FACTORS=2
AI_CONFIRM_PROB_UP_THRESHOLD=0.55
AI_CONFIRM_PROB_DOWN_THRESHOLD=0.55
AI_CONFIRM_CONFIDENCE_THRESHOLD=0.45

# ── SL/TP Ratio ──
ATR_SL_MULTIPLIER=1.5       # SL แคบ แต่ไม่โดน noise
ATR_TP_MULTIPLIER=3.0       # TP กว้าง 2-3x SL

# ── Volume Limits ──
MIN_VOLUME=0.01
MAX_VOLUME=1.0

# ── Session Filter (เทรดเฉพาะ London/NY เปิด) ──
SESSION_FILTER_ENABLED=true
SESSION_ACTIVE_HOURS=07:00-17:00   # UTC

# ── Auto Trade ──
AUTO_TRADE_ENABLED=true
```

### ขั้นตอนเริ่มต้น

```bash
# 1. ติดตั้ง
pip install -r requirements.txt
cp .env.example .env
# แก้ไข .env ตามค่าข้างบน + ใส่ข้อมูล MT5

# 2. เริ่มรันบัญชี DEMO ก่อน (ทดสอบ 1-2 สัปดาห์)
python main.py

# 3. เทรน LSTM โดยดึงข้อมูลย้อนหลังจาก MT5 โดยตรง (ไม่ต้องรอเก็บ log)
python -m scripts.train_ai

# 4. รัน dashboard ดู real-time
uvicorn dashboard.server:app --reload

# 5. ดู AI accuracy ว่าดีพอไหม
curl http://localhost:8000/api/eval_ai?horizon=5
```

### ตัวอย่างการคำนวณ Position Size

สมมติบัญชี 10,000 USD, ATR = 2.5, TICK_SIZE=0.1, TICK_VALUE=1.0:

```
risk_amount  = 10,000 × 0.01 = $100
sl_distance  = 1.5 × 2.5 = 3.75 points
sl_points    = 3.75 / 0.1 = 37.5 ticks
cost_per_lot = 37.5 × 1.0 = $37.5
volume       = $100 / $37.5 = 2.67 lot → capped ≤ 1.0 lot (MAX_VOLUME)
```

> หมายเหตุ: ปรับ `TICK_VALUE` และ `TICK_SIZE` ให้ตรงกับโบรกของคุณ

---

## ▶️ การรันระบบ

### รันทุกอย่างพร้อมกัน (แนะนำ)

```bash
python run_all.py
```

### รันแยก

```bash
# รัน AI Bot Loop
python main.py

# รัน Dashboard (terminal แยก)
uvicorn dashboard.server:app --host 0.0.0.0 --port 8000 --reload
```

เปิดเว็บ: [http://localhost:8000](http://localhost:8000)

---

## 📊 AI Signal Logic

### PRE Signal (เตือนล่วงหน้า)

ส่งสัญญาณเตือนเมื่อผ่าน **2 ใน 5** เงื่อนไข:

| เงื่อนไข | อธิบาย |
|---------|--------|
| RSI Oversold/Overbought | RSI < 30 หรือ > 70 |
| MACD momentum | |MACD Hist| > 0.15 |
| AI confidence | Confidence > 0.55 |
| EMA aligned | EMA Trend score ≥ 1 |
| BB extreme | BB %B < 20% หรือ > 80% |

### CONFIRM Signal (ยืนยันเข้าไม้)

ต้องผ่าน **ทุก** เงื่อนไขต่อไปนี้:
1. AI prob_up/prob_down เกิน threshold (ตาม AI_MODE)
2. MACD ไม่ขัดแย้งทิศทาง
3. AI confidence เกิน threshold
4. Confirmation factors ≥ `MIN_CONFIRM_FACTORS`

### Confirmation Factors (BUY ตัวอย่าง)

| Factor | เงื่อนไข |
|--------|---------|
| EMA Trend | EMA9 > EMA21 หรือ EMA21 > EMA50 |
| BB Position | BB %B < 35% (ราคาใกล้ lower band) |
| Stochastic | %K < 40 (oversold zone) |
| Candlestick | Bullish Engulfing หรือ Hammer |
| Volume | Volume ratio > 1.3x ค่าเฉลี่ย |

---

## 🛡️ Risk Management

### Dynamic SL/TP Matrix

| Regime | SL Multiplier | RR Ratio |
|--------|--------------|----------|
| trending (high conf) | 1.8x ATR | 1:2.5 |
| trending (med conf) | 1.6x ATR | 1:2.0 |
| reversal | 1.5x ATR | 1:2.0 |
| sideways | 1.2x ATR | 1:1.4 |
| volatile | 2.2x ATR | 1:1.5 |

### Drawdown Protection

บอทจะลด position size อัตโนมัติเมื่อ:
- Drawdown > 5% → ลด size 25%
- Drawdown > 10% → ลด size 50%

ตั้งค่า `INITIAL_BALANCE` ให้ตรงกับทุนเริ่มต้นของคุณ

### Kelly Criterion (Optional)

เปิดใช้งานเพื่อให้ AI คำนวณ optimal lot size จาก win rate ที่ผ่านมา:

```env
KELLY_CRITERION_ENABLED=true
KELLY_FRACTION=0.5    # Half-Kelly (แนะนำ ลดความเสี่ยงครึ่งหนึ่ง)
```

---

## 🤖 LLM Advisor (GPT + Gemini)

เพิ่มชั้น AI ภาษาธรรมชาติ ยืนยันสัญญาณก่อนเข้าไม้

### เปิดใช้งาน

```env
LLM_ADVISOR_ENABLED=true
LLM_REQUIRE_CONSENSUS=true    # บังคับ LLM เห็นด้วยก่อนเข้าไม้

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini      # ประหยัด หรือ gpt-4o สำหรับความแม่นยำสูงสุด

GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash  # ฟรี/ประหยัด หรือ gemini-1.5-pro
```

### ข้อมูลที่ส่งให้ LLM

LLM จะได้รับ snapshot ครบถ้วน รวมถึง:
- RSI, MACD, Stochastic
- EMA alignment (9/21/50)
- Bollinger Band position (%B)
- Volume vs average
- Market regime
- AI probability + reasoning
- Proposed trade direction

### Consensus Logic

| สถานการณ์ | ผลลัพธ์ |
|----------|--------|
| ทั้งสองเห็นด้วย | ดำเนินการ (confidence สูง) |
| แตกต่างกัน มาก (>20%) | ใช้ค่าที่มั่นใจกว่า |
| แตกต่างกัน ใกล้เคียง | HOLD (ข้ามไม้นี้) |
| ไม่มี API key | Pass-through (ใช้ technical AI ปกติ) |

---

## 🏋️ การเทรน LSTM

### เริ่มต้น

ไม่ต้องรอเก็บ log ในเครื่อง — สคริปต์ดึงข้อมูล OHLCV ย้อนหลังจาก MT5 โดยตรง  
เพียงแค่ MT5 เชื่อมต่อได้ก็เทรนได้ทันที:

```bash
python -m scripts.train_ai
```

สคริปต์จะ:
1. เชื่อมต่อ MT5 (ใช้ MT5_LOGIN / MT5_PASSWORD / MT5_SERVER ใน `.env`)
2. ดึงข้อมูล OHLCV ย้อนหลัง `TRAIN_BARS` แท่ง (ค่าเริ่มต้น 5,000 แท่ง) มาโดยตรง
3. คำนวณ indicators ครบชุด (RSI, MACD, ATR, ADX, EMA, BB, Stoch, Volume)
4. สร้าง feature matrix (60 แท่ง × 7 features) และเทรน LSTM 5 epochs
5. บันทึก `models/extreme_lstm.keras` + `logs/last_train.json`

หลังเทรนเสร็จ บอทจะใช้ LSTM อัตโนมัติ (LSTM 70% + Rule-based 30%)

### ปรับจำนวนแท่งสำหรับเทรน

```env
TRAIN_BARS=5000   # ค่าเริ่มต้น — แนะนำ 3000–10000
```

> ยิ่งมากแท่ง → model แม่นขึ้น แต่ใช้เวลาเทรนนานขึ้นเล็กน้อย

### ตรวจสอบ AI Performance

```bash
# ดู accuracy จาก log (horizon = 5 แท่งข้างหน้า)
curl "http://localhost:8000/api/eval_ai?horizon=5"
```

ผลที่ดี:
- `direction_acc` > 0.55 (55%+)
- `winrate` > 0.50 (50%+)  
- `avg_pnl` > 0 (positive expectancy)

---

## 🖥️ Dashboard Web

### เปิด Dashboard

```bash
uvicorn dashboard.server:app --host 0.0.0.0 --port 8000
```

เปิดเว็บ: [http://localhost:8000](http://localhost:8000)

### ฟีเจอร์ Dashboard

- **Real-time price + AI probability** (อัปเดตทุก 1 วินาที)
- **Market regime** (trending/sideways/reversal/volatile)
- **EMA trend, BB %B, Stochastic** indicators
- **AI confidence bar** + Rule vs LSTM comparison
- **LLM reasoning** (ถ้าเปิดใช้)
- **ปุ่ม BUY / SELL / AUTO** สำหรับ manual trade
- **ปุ่ม Train AI** เรียก retrain LSTM โดยตรง
- **Open trades counter + balance**

### API Endpoints

| Endpoint | วิธีใช้ |
|---------|--------|
| `GET /` | Dashboard UI |
| `WS /ws` | WebSocket real-time state |
| `POST /api/order` | ส่งออเดอร์ `{"side": "BUY"/"SELL"/"AUTO"}` |
| `POST /api/train_ai` | เรียก retrain LSTM |
| `GET /api/eval_ai?horizon=5` | ดู AI accuracy |

---

## 📱 Discord Notifications

### ตั้งค่า Webhook

1. Discord → Server Settings → Integrations → Webhooks
2. สร้าง Webhook ใหม่ → Copy URL
3. ใส่ใน `.env`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### ประเภทการแจ้งเตือน

| Type | เมื่อไหร่ |
|------|----------|
| 🚀 Bot Started | เริ่มรัน main.py |
| 🔔 PRE Signal | สัญญาณเบื้องต้น (+ chart) |
| ✅ CONFIRM Signal | สัญญาณยืนยัน (+ chart) |
| 🤖 Executed Trade | เปิดออเดอร์จริง |
| ⚠️ Error | เกิด error ในระบบ |

---

## 🎛️ การปรับแต่ง AI Mode

### SAFE mode (เน้นคุณภาพ)

```env
AI_MODE=SAFE
MIN_CONFIRM_FACTORS=3
AI_CONFIRM_PROB_UP_THRESHOLD=0.65
AI_CONFIRM_CONFIDENCE_THRESHOLD=0.60
```

เหมาะสำหรับ: มือใหม่, ทุนน้อย, ต้องการลดความถี่การเทรด

### NORMAL mode (สมดุล — แนะนำ)

```env
AI_MODE=NORMAL
MIN_CONFIRM_FACTORS=2
AI_CONFIRM_PROB_UP_THRESHOLD=0.55
AI_CONFIRM_CONFIDENCE_THRESHOLD=0.45
```

เหมาะสำหรับ: ทุน 10,000+ ต้องการสมดุลระหว่าง quality และ frequency

### AGGRESSIVE mode (เน้นโอกาส)

```env
AI_MODE=AGGRESSIVE
MIN_CONFIRM_FACTORS=1
AI_CONFIRM_PROB_UP_THRESHOLD=0.53
AI_CONFIRM_CONFIDENCE_THRESHOLD=0.35
```

เหมาะสำหรับ: ผู้มีประสบการณ์, ทุนมาก, ยอมรับความเสี่ยงสูงกว่า

---

## 🔧 Troubleshooting

### MT5 ไม่ connect

```
[MT5] initialize() failed
[MT5] login() failed
```

**แก้ไข:**
- ตรวจสอบ MetaTrader 5 เปิดอยู่บนเครื่อง
- ตรวจสอบ MT5_SERVER ตรงกับชื่อ server จากโบรก
- ตรวจสอบ MT5_LOGIN และ MT5_PASSWORD ถูกต้อง
- บน Linux/Mac: MT5 ต้องรันผ่าน Wine หรือใช้ VPS Windows

### ไม่มีสัญญาณ (ไม่เห็น CONFIRM signal)

**แก้ไข:**
- ลอง `AI_MODE=AGGRESSIVE` ก่อนเพื่อทดสอบว่าสัญญาณออก
- ลด `AI_CONFIRM_PROB_UP_THRESHOLD` เป็น `0.52`
- ลด `MIN_CONFIRM_FACTORS` เป็น `1`
- ตรวจสอบว่า data ดึงได้ (`[LOOP] XAUUSD price=...` ควรปรากฏ)

### LSTM ไม่โหลด

```
[AI] LSTM model not found, using Rule-based only.
```

**แก้ไข:**
- รัน `python -m scripts.train_ai` (MT5 ต้องเชื่อมต่ออยู่)
- ตรวจว่าไฟล์ `models/extreme_lstm.keras` มีอยู่

### Train AI ล้มเหลว

```
[TRAIN_AI] ❌ MT5 connect failed.
```

**แก้ไข:**
- ตรวจสอบ MetaTrader 5 เปิดอยู่บนเครื่อง
- ตรวจสอบ `MT5_LOGIN` / `MT5_PASSWORD` / `MT5_SERVER` ใน `.env` ถูกต้อง
- ตรวจสอบ `SYMBOL` และ `TIMEFRAME` ตรงกับที่โบรกรองรับ

### LLM Error

```
[LLM][GPT] error: ...
```

**แก้ไข:**
- ตรวจสอบ API key ถูกต้องและมี quota
- ลอง `LLM_ADVISOR_ENABLED=false` เพื่อข้ามไปก่อน

### Dashboard ไม่แสดงข้อมูล

**แก้ไข:**
- ตรวจสอบว่า `main.py` รันอยู่ (dashboard ดึงข้อมูลจาก `logs/last_state.json`)
- ตรวจสอบว่า `logs/` folder มีอยู่

---

## 📝 หมายเหตุสำคัญ

1. **Demo ก่อนเสมอ** — ทดสอบบัญชี Demo อย่างน้อย 2 สัปดาห์ก่อนใช้เงินจริง
2. **TICK_VALUE / TICK_SIZE** — ต้องกรอกให้ตรงกับโบรกของคุณ (ค่าผิด = position size ผิด)
3. **SYMBOL** — ชื่ออาจต่างกันตามโบรก เช่น `XAUUSDm`, `XAUUSD`, `GOLD`
4. **Backtest** — ดู `scripts/backtest.py` สำหรับทดสอบย้อนหลัง
5. **Log Rotation** — ไฟล์ log บันทึกแยกตามวัน (`ai_log_YYYY-MM-DD.jsonl`)
6. **Auto Trade** — ตั้ง `AUTO_TRADE_ENABLED=false` ก่อน จนกว่าจะมั่นใจในสัญญาณ

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **pandas / numpy** — Data processing
- **PyTorch** — LSTM model
- **FastAPI + Uvicorn** — Web dashboard
- **MetaTrader5** — Broker integration
- **openai / google-generativeai** — LLM advisors
- **matplotlib** — Chart generation
- **python-dotenv** — Config management

