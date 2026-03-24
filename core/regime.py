import pandas as pd


def detect_regime(df: pd.DataFrame) -> str:
    """
    ตรวจจับ Market Regime แบบ Multi-factor:
    - trending   : ADX สูง + EMA aligned + BB กว้าง
    - sideways   : ADX ต่ำ + BB แคบ (squeeze) + ราคาในกรอบ
    - reversal   : สัญญาณกลับทิศ (EMA cross, BB bounce, ราคาพลิก)
    - volatile   : BB กว้างมาก + ATR สูง (ระวังสูง)
    คืนค่า: "trending" | "sideways" | "reversal" | "volatile" | "unknown"
    """
    if len(df) < 50:
        return "unknown"

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    adx_val = float(last.get("ADX", 0))
    ema_trend = float(last.get("EMA_TREND", 0))
    prev_ema_trend = float(prev.get("EMA_TREND", 0))
    bb_width = float(last.get("BB_WIDTH", 0))
    bb_pct_b = float(last.get("BB_PCT_B", 0.5))
    atr_val = float(last.get("ATR", 0))
    close = float(last.get("Close", 0))

    # คำนวณ BB width เฉลี่ย 20 แท่ง (เพื่อเปรียบเทียบ)
    if "BB_WIDTH" in df.columns and len(df) >= 20:
        bb_width_avg = float(df["BB_WIDTH"].iloc[-20:].mean())
    else:
        bb_width_avg = bb_width

    # ATR เฉลี่ย 20 แท่ง (เปรียบเทียบ volatility)
    if "ATR" in df.columns and len(df) >= 20:
        atr_avg = float(df["ATR"].iloc[-20:].mean())
    else:
        atr_avg = atr_val

    # ── Volatile: ATR สูงกว่าค่าเฉลี่ยมาก + BB กว้างมาก ──────────────
    if atr_val > atr_avg * 1.8 and bb_width > bb_width_avg * 1.5:
        return "volatile"

    # ── Trending: ADX สูง + EMA aligned ──────────────────────────────
    if adx_val > 25 and abs(ema_trend) >= 1:
        return "trending"

    # ── Reversal: EMA trend เปลี่ยน + BB extreme bounce ───────────────
    ema_trend_changed = (ema_trend > 0 and prev_ema_trend < 0) or (ema_trend < 0 and prev_ema_trend > 0)
    bb_bounce = (bb_pct_b < 0.10 and ema_trend > 0) or (bb_pct_b > 0.90 and ema_trend < 0)
    if ema_trend_changed or bb_bounce:
        return "reversal"

    # ── Sideways: ADX ต่ำ + BB แคบ (squeeze) ────────────────────────
    if adx_val < 20 and bb_width < bb_width_avg * 0.85:
        return "sideways"

    # Default: trending ถ้า ADX พอสมควร
    if adx_val > 18:
        return "trending"

    return "sideways"
