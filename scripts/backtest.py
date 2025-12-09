# scripts/backtest.py

import json
import os
from dataclasses import dataclass
from typing import List

import pandas as pd

from core.config import settings
from core.indicators import add_all_indicators
from core.ai_engine import ExtremeAIEngine


@dataclass
class Trade:
    entry_time: str
    exit_time: str | None
    side: str
    entry_price: float
    exit_price: float | None
    sl: float
    tp: float
    result_r: float | None  # กี่เท่าของ risk


def backtest(csv_path: str):
    df_raw = pd.read_csv(csv_path, parse_dates=["time"])
    df_raw = df_raw.sort_values("time")

    ai = ExtremeAIEngine()

    trades: List[Trade] = []
    open_trade: Trade | None = None

    for i in range(200, len(df_raw)):
        df_slice = df_raw.iloc[: i + 1].copy()
        df = add_all_indicators(df_slice)
        if df.empty:
            continue

        last = df.iloc[-1]
        time_ = last["time"]
        price = float(last["Close"])
        atr = float(last["ATR"])
        adx = float(last["ADX"])

        ai_res = ai.compute_ai(df)
        prob_up = ai_res["prob_up"]
        prob_down = ai_res["prob_down"]
        confidence = ai_res["confidence"]
        macd_hist = float(last["MACD_HIST"])

        # ปิดไม้ถ้ามี open trade
        if open_trade is not None:
            if open_trade.side == "BUY":
                if price <= open_trade.sl or price >= open_trade.tp:
                    r = (
                        (open_trade.tp - open_trade.entry_price)
                        / (open_trade.entry_price - open_trade.sl)
                        if price >= open_trade.tp
                        else (open_trade.sl - open_trade.entry_price)
                        / (open_trade.entry_price - open_trade.sl)
                    )
                    open_trade.exit_time = str(time_)
                    open_trade.exit_price = price
                    open_trade.result_r = r
                    trades.append(open_trade)
                    open_trade = None
            else:
                if price >= open_trade.sl or price <= open_trade.tp:
                    r = (
                        (open_trade.entry_price - open_trade.tp)
                        / (open_trade.sl - open_trade.entry_price)
                        if price <= open_trade.tp
                        else (open_trade.entry_price - open_trade.sl)
                        / (open_trade.sl - open_trade.entry_price)
                    )
                    open_trade.exit_time = str(time_)
                    open_trade.exit_price = price
                    open_trade.result_r = r
                    trades.append(open_trade)
                    open_trade = None

        # ถ้ามีไม้เปิดอยู่แล้ว → ไม่เปิดใหม่
        if open_trade is not None:
            continue

        # ฟิลเตอร์ ADX
        if adx < settings.ADX_TREND_THRESHOLD:
            continue

        # logic CONFIRM แบบเดียวกับ main
        confirm_side = None
        if prob_up > 0.70 and macd_hist > 0 and confidence > 0.6:
            confirm_side = "BUY"
        elif prob_down > 0.70 and macd_hist < 0 and confidence > 0.6:
            confirm_side = "SELL"

        if confirm_side is None:
            continue

        sl_dist = settings.ATR_SL_MULTIPLIER * atr
        tp_dist = settings.ATR_TP_MULTIPLIER * atr

        if confirm_side == "BUY":
            sl = price - sl_dist
            tp = price + tp_dist
        else:
            sl = price + sl_dist
            tp = price - tp_dist

        open_trade = Trade(
            entry_time=str(time_),
            exit_time=None,
            side=confirm_side,
            entry_price=price,
            exit_price=None,
            sl=sl,
            tp=tp,
            result_r=None,
        )

    # ถ้าไม้สุดท้ายยังไม่ปิดก็ทิ้ง
    if open_trade is not None:
        trades.append(open_trade)

    # สรุปผล
    Rs = [t.result_r for t in trades if t.result_r is not None]
    wins = [r for r in Rs if r > 0]
    losses = [r for r in Rs if r <= 0]

    print(f"Backtest trades: {len(Rs)}")
    print(f"Wins: {len(wins)}, Losses: {len(losses)}")
    if Rs:
        print(f"Avg R: {sum(Rs)/len(Rs):.2f}")
    if wins:
        print(f"Avg Win R: {sum(wins)/len(wins):.2f}")
    if losses:
        print(f"Avg Loss R: {sum(losses)/len(losses):.2f}")

    os.makedirs("logs", exist_ok=True)
    with open("logs/backtest_trades.json", "w", encoding="utf-8") as f:
        json.dump([t.__dict__ for t in trades], f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # เตรียมไฟล์ CSV: time,Open,High,Low,Close,Volume
    backtest("data/backtest_XAUUSD.csv")
