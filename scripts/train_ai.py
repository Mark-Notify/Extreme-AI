import json
import os

import pandas as pd

from core.config import settings
from core.indicators import add_all_indicators
from core.lstm_model import ExtremeLSTM


def load_ai_log(path: str) -> pd.DataFrame:
    # เดิม: if not os.path.exists(path): raise FileNotFoundError(path)
    # แก้เป็น: ถ้าไม่เจอไฟล์ ให้แจ้งแล้วคืน DataFrame ว่าง ๆ
    if not os.path.exists(path):
        print(f"[TRAIN_AI] log file not found: {path}")
        return pd.DataFrame()

    rows = []
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
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df.sort_values("time", inplace=True)
    return df


def main():
    print("[TRAIN_AI] loading logs from", settings.AI_LOG_PATH)
    df_log = load_ai_log(settings.AI_LOG_PATH)

    # กันเคสไม่มี log หรืออ่านแล้วว่าง
    if df_log.empty:
        print("[TRAIN_AI] no log data to train, run main.py ก่อนให้มี logs/ai_log.jsonl")
        return

    df_price = df_log[["time", "close"]].copy()
    df_price.rename(columns={"time": "time", "close": "Close"}, inplace=True)
    df_price["Open"] = df_price["Close"]
    df_price["High"] = df_price["Close"]
    df_price["Low"] = df_price["Close"]
    df_price["Volume"] = 0

    df_ind = add_all_indicators(df_price)
    if df_ind.empty:
        print("[TRAIN_AI] no indicator data")
        return

    model = ExtremeLSTM()
    print("[TRAIN_AI] start training...")
    model.fit(df_ind, epochs=5, batch_size=32)
    os.makedirs(os.path.dirname(settings.LSTM_MODEL_PATH), exist_ok=True)
    model.save(settings.LSTM_MODEL_PATH)
    print("[TRAIN_AI] Saved model to", settings.LSTM_MODEL_PATH)


if __name__ == "__main__":
    main()
