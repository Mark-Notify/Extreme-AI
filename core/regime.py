import pandas as pd


def detect_regime(df: pd.DataFrame) -> str:
    """
    คืนค่า: trending / sideways / reversal
    logic แบบง่าย ๆ อิงจาก ADX + slope ราคา
    """
    if len(df) < 20:
        return "unknown"

    last = df.iloc[-1]
    adx = last.get("ADX", 0)
    close = df["Close"]
    slope = (close.iloc[-1] - close.iloc[-10]) / (10 + 1e-9)

    if adx > 25 and abs(slope) > 0:
        return "trending"
    if adx < 15 and abs(slope) < (close.iloc[-1] * 0.0005):
        return "sideways"
    if slope * (close.diff().iloc[-1]) < 0:
        return "reversal"

    return "trending"
