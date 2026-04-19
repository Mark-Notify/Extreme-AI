"""ดึงข้อมูล OHLCV ย้อนหลังจาก MT5 โดยตรงแล้วเทรน LSTM
ไม่ต้องรอเก็บ log ในเครื่อง — เพียงแค่ MT5 เชื่อมต่อได้ก็เทรนได้ทันที
"""

import json
import os
from datetime import datetime, timezone

from core.config import settings
from core.data_feed import init_mt5, get_recent_ohlc
from core.indicators import add_all_indicators
from core.lstm_model import ExtremeLSTM


def main():
    print("[TRAIN_AI] connecting to MT5...")
    ok = init_mt5()
    if not ok:
        print(
            "[TRAIN_AI] ❌ MT5 connect failed. "
            "ตรวจสอบ MT5_LOGIN / MT5_PASSWORD / MT5_SERVER ใน .env "
            "และให้ MetaTrader 5 เปิดอยู่บนเครื่อง"
        )
        return

    bars = settings.TRAIN_BARS
    symbol = settings.SYMBOL
    timeframe = settings.TIMEFRAME

    print(f"[TRAIN_AI] fetching {bars} bars of {symbol} {timeframe} from MT5...")
    df_raw = get_recent_ohlc(symbol, timeframe, bars)
    if df_raw is None or df_raw.empty:
        print(
            "[TRAIN_AI] ❌ ไม่ได้รับข้อมูลจาก MT5 "
            "ตรวจสอบ SYMBOL / TIMEFRAME ใน .env ว่าตรงกับที่โบรกใช้"
        )
        return

    print(
        f"[TRAIN_AI] got {len(df_raw)} bars "
        f"({df_raw['time'].iloc[0]} → {df_raw['time'].iloc[-1]})"
    )

    df_ind = add_all_indicators(df_raw)
    if df_ind.empty:
        print("[TRAIN_AI] ❌ no indicator data after transform")
        return

    print(f"[TRAIN_AI] indicator rows: {len(df_ind)}")

    model = ExtremeLSTM()
    print("[TRAIN_AI] start training...")
    model.fit(df_ind, epochs=5, batch_size=32)

    os.makedirs(os.path.dirname(settings.LSTM_MODEL_PATH), exist_ok=True)
    model.save(settings.LSTM_MODEL_PATH)
    print("[TRAIN_AI] ✅ saved model to", settings.LSTM_MODEL_PATH)

    meta = {
        "last_train_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "samples": int(len(df_ind)),
        "bars_fetched": int(len(df_raw)),
        "symbol": symbol,
        "timeframe": timeframe,
        "epochs": 5,
        "source": "MT5",
    }
    os.makedirs("logs", exist_ok=True)
    with open("logs/last_train.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print("[TRAIN_AI] wrote logs/last_train.json")


if __name__ == "__main__":
    main()
