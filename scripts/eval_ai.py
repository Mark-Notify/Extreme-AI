import json
import os

import numpy as np
import pandas as pd
from datetime import datetime


LOG_PATH = f"logs/ai_log_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
HORIZON_BARS = 5   # ดูผลลัพธ์ในอนาคตอีกกี่แท่ง (เช่น 5 แท่ง = 5 * TF)


def load_ai_log(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
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


def evaluate_direction(df: pd.DataFrame, horizon: int = 5, only_confirm: bool = False):
    df = df.copy()

    if only_confirm:
        df = df[df.get("confirm_signal", False)].copy()
        if df.empty:
            print("⚠ ไม่มีแถวที่เป็น confirm_signal ใน log นี้")
            return

    # future_ret = ผลตอบแทนในอนาคต (อีก horizon แท่งข้างหน้า)
    # ถ้า timeframe = M1, horizon=5 → ประมาณ 5 นาที
    df["future_close"] = df["close"].shift(-horizon)
    df["future_ret"] = df["future_close"] / df["close"] - 1.0
    df = df.dropna(subset=["future_ret"])

    # ทิศที่ AI ทาย: 1 = UP, -1 = DOWN
    df["pred_dir"] = np.where(df["ai_prob_up"] >= df["ai_prob_down"], 1, -1)

    # ทิศจริงในอนาคต
    df["true_dir"] = np.sign(df["future_ret"]).replace(0, 0)

    # ถูก/ผิด
    df["correct"] = df["pred_dir"] == df["true_dir"]

    # ถ้าตาม AI เข้าไม้ long/short ทันทีที่ทาย
    df["pnl"] = np.where(df["pred_dir"] == 1, df["future_ret"], -df["future_ret"])

    total = len(df)
    acc = df["correct"].mean() if total else 0.0
    winrate = (df["pnl"] > 0).mean() if total else 0.0
    avg_pnl = df["pnl"].mean() if total else 0.0

    avg_win = df.loc[df["pnl"] > 0, "pnl"].mean()
    avg_loss = -df.loc[df["pnl"] < 0, "pnl"].mean()

    print("=" * 60)
    print("EVAL AI DIRECTION - horizon =", horizon, "bars",
          "| only_confirm =", only_confirm)
    print("samples:", total)
    print(f"direction accuracy : {acc*100:5.2f}%")
    print(f"winrate (pnl>0)    : {winrate*100:5.2f}%")
    print(f"avg pnl per trade  : {avg_pnl*10000:7.2f} points (x1e-4)")
    print(f"avg win / avg loss : {avg_win*10000:7.2f} / {avg_loss*10000:7.2f}")
    print("=" * 60)

    return df


def evaluate_by_confidence(df: pd.DataFrame):
    df = df.copy()
    df = df.dropna(subset=["future_ret"])

    df["pred_dir"] = np.where(df["ai_prob_up"] >= df["ai_prob_down"], 1, -1)
    df["true_dir"] = np.sign(df["future_ret"]).replace(0, 0)
    df["correct"] = df["pred_dir"] == df["true_dir"]

    df["pnl"] = np.where(df["pred_dir"] == 1, df["future_ret"], -df["future_ret"])

    # confidence = |prob_up - 0.5|*2 (0-1) ถ้าไม่มีใน log เราคิดเองได้
    if "ai_confidence" not in df.columns:
        df["ai_confidence"] = (df["ai_prob_up"] - 0.5).abs() * 2

    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.01]
    labels = ["0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
    df["conf_bin"] = pd.cut(df["ai_confidence"], bins=bins, labels=labels)

    print("EVAL BY CONFIDENCE BIN")
    g = df.groupby("conf_bin")
    for name, sub in g:
        if sub.empty:
            continue
        acc = sub["correct"].mean()
        winrate = (sub["pnl"] > 0).mean()
        avg_pnl = sub["pnl"].mean()
        print(
            f"  conf={name:6s} | n={len(sub):4d} | "
            f"acc={acc*100:5.1f}% | winrate={winrate*100:5.1f}% | "
            f"avg_pnl={avg_pnl*10000:7.2f}"
        )


def main():
    print("[EVAL_AI] load log from", LOG_PATH)
    df = load_ai_log(LOG_PATH)

    if df.empty:
        print("⚠ log ว่าง ไม่มีข้อมูลให้ประเมิน")
        return

    # ปรับชื่อ column ให้ตรง (เผื่อใน log คุณใช้ชื่ออื่น)
    if "close" not in df.columns and "Close" in df.columns:
        df["close"] = df["Close"]

    # ประเมินทุกแท่ง (เสมือนเข้าไม้ทุกครั้งที่ AI ทาย)
    df_all = evaluate_direction(df, horizon=HORIZON_BARS, only_confirm=False)

    # ประเมินเฉพาะจุดที่มี confirm_signal (สัญญาณเทรดจริง)
    df_conf = evaluate_direction(df, horizon=HORIZON_BARS, only_confirm=True)

    # ทำ future_ret ทิ้งไว้สำหรับ confidence bin
    df_all["future_close"] = df_all["close"].shift(-HORIZON_BARS)
    df_all["future_ret"] = df_all["future_close"] / df_all["close"] - 1.0
    df_all = df_all.dropna(subset=["future_ret"])

    evaluate_by_confidence(df_all)


if __name__ == "__main__":
    main()
