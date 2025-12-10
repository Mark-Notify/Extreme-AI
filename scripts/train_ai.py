import glob
import json
import os
from datetime import datetime, timedelta

import pandas as pd

from core.config import settings
from core.indicators import add_all_indicators
from core.lstm_model import ExtremeLSTM


def load_recent_ai_logs(days: int = 3) -> pd.DataFrame:
    """
    อ่าน log หลายไฟล์ล่าสุด เช่น ai_log_YYYY-MM-DD.jsonl ในช่วง N วันหลัง
    """
    base_dir = os.path.dirname(settings.AI_LOG_PATH) or "logs"
    pattern = os.path.join(base_dir, "ai_log_*.jsonl")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(pattern)

    cutoff = datetime.utcnow().date() - timedelta(days=days - 1)
    selected = []

    # ไล่จากไฟล์ใหม่ไปเก่า
    for path in reversed(files):
        name = os.path.basename(path)  # ai_log_YYYY-MM-DD.jsonl
        try:
            date_str = name.replace("ai_log_", "").replace(".jsonl", "")
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            continue
        if d >= cutoff:
            selected.append(path)

    # ถ้าไม่มีไฟล์ในช่วง N วัน ให้ fallback เป็นไฟล์ล่าสุดไฟล์เดียว
    if not selected:
        selected = [files[-1]]

    rows = []
    for path in selected:
        print(f"[TRAIN_AI] read log: {path}")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df.sort_values("time", inplace=True)

    return df


def main():
    base_dir = os.path.dirname(settings.AI_LOG_PATH) or "logs"
    print("[TRAIN_AI] loading recent logs from", base_dir)

    try:
        df_log = load_recent_ai_logs(days=3)
    except FileNotFoundError as e:
        print("[TRAIN_AI] no log files found:", e)
        return

    if df_log.empty:
        print("[TRAIN_AI] no log rows to train")
        return

    # ใช้ time + close ทำเป็น pseudo OHLC
    df_price = df_log[["time", "close"]].copy()
    df_price.rename(columns={"time": "time", "close": "Close"}, inplace=True)
    df_price["Open"] = df_price["Close"]
    df_price["High"] = df_price["Close"]
    df_price["Low"] = df_price["Close"]
    df_price["Volume"] = 0

    df_ind = add_all_indicators(df_price)
    if df_ind.empty:
        print("[TRAIN_AI] no indicator data after transform")
        return

    model = ExtremeLSTM()
    print("[TRAIN_AI] start training...")
    model.fit(df_ind, epochs=5, batch_size=32)

    os.makedirs(os.path.dirname(settings.LSTM_MODEL_PATH), exist_ok=True)
    model.save(settings.LSTM_MODEL_PATH)
    print("[TRAIN_AI] Saved model to", settings.LSTM_MODEL_PATH)

    # บันทึก meta สำหรับ Dashboard (เวลาที่ train ล่าสุด ฯลฯ)
    meta = {
        "last_train_time": datetime.utcnow().isoformat() + "Z",
        "samples": int(len(df_ind)),
        "epochs": 5,
    }
    os.makedirs("logs", exist_ok=True)
    with open("logs/last_train.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print("[TRAIN_AI] wrote logs/last_train.json")


if __name__ == "__main__":
    main()
