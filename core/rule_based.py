from typing import Dict
import pandas as pd


def compute_rule_based_prob(df: pd.DataFrame) -> Dict:
    """
    Rule-based Extreme AI (fallback)
    คืนค่า probability แบบง่าย ๆ ตาม RSI/MACD/Trend
    """
    last = df.iloc[-1]
    rsi = last["RSI"]
    macd_hist = last["MACD_HIST"]
    adx = last["ADX"]

    prob_up = 0.5
    prob_down = 0.5
    reasons = []

    # RSI zone
    if rsi < 30:
        prob_up += 0.2
        reasons.append("RSI oversold")
    elif rsi > 70:
        prob_down += 0.2
        reasons.append("RSI overbought")

    # MACD histogram
    if macd_hist > 0:
        prob_up += 0.15
        reasons.append("MACD hist > 0")
    elif macd_hist < 0:
        prob_down += 0.15
        reasons.append("MACD hist < 0")

    # Trend strength from ADX
    if adx > 25:
        reasons.append("Strong trend (ADX>25)")

    # Normalize
    s = prob_up + prob_down
    if s == 0:
        prob_up = prob_down = 0.5
    else:
        prob_up /= s
        prob_down /= s

    return {
        "prob_up": float(prob_up),
        "prob_down": float(prob_down),
        "reasons": reasons,
    }
