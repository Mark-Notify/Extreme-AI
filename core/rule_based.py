from typing import Dict
import pandas as pd


def compute_rule_based_prob(df: pd.DataFrame) -> Dict:
    """
    Rule-based Extreme AI — Multi-factor scoring system

    Factors (weighted):
    1. RSI zone (oversold/overbought) — mean reversion + trend
    2. MACD histogram direction + crossover
    3. EMA trend alignment (9/21/50)
    4. Bollinger Band position + squeeze breakout
    5. Stochastic (%K/%D) crossover
    6. ADX trend strength (filter)
    7. Volume confirmation
    8. Candlestick patterns
    """
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    rsi_val = float(last.get("RSI", 50))
    macd_hist = float(last.get("MACD_HIST", 0))
    prev_macd_hist = float(prev.get("MACD_HIST", 0))
    adx_val = float(last.get("ADX", 0))
    ema_trend = float(last.get("EMA_TREND", 0))
    bb_pct_b = float(last.get("BB_PCT_B", 0.5))
    bb_width = float(last.get("BB_WIDTH", 0))
    prev_bb_width = float(prev.get("BB_WIDTH", 0))
    stoch_k = float(last.get("STOCH_K", 50))
    stoch_d = float(last.get("STOCH_D", 50))
    prev_stoch_k = float(prev.get("STOCH_K", 50))
    prev_stoch_d = float(prev.get("STOCH_D", 50))
    vol_ratio = float(last.get("VOL_RATIO", 1.0))
    bullish_engulf = int(last.get("BULLISH_ENGULF", 0))
    bearish_engulf = int(last.get("BEARISH_ENGULF", 0))
    hammer = int(last.get("HAMMER", 0))
    shooting_star = int(last.get("SHOOTING_STAR", 0))
    close = float(last.get("Close", 0))
    ema9 = float(last.get("EMA9", close))
    ema21 = float(last.get("EMA21", close))

    score_up = 0.0
    score_down = 0.0
    reasons = []

    # ── 1) RSI ──────────────────────────────────────────────────────
    if rsi_val < 30:
        score_up += 0.20
        reasons.append(f"RSI oversold ({rsi_val:.1f})")
    elif rsi_val < 40:
        score_up += 0.08
        reasons.append(f"RSI low ({rsi_val:.1f})")
    elif rsi_val > 70:
        score_down += 0.20
        reasons.append(f"RSI overbought ({rsi_val:.1f})")
    elif rsi_val > 60:
        score_down += 0.08
        reasons.append(f"RSI high ({rsi_val:.1f})")

    # RSI midline cross (50 level momentum)
    if 45 < rsi_val < 55:
        if rsi_val > 50 and prev.get("RSI", 50) < 50:
            score_up += 0.06
            reasons.append("RSI crossed above 50")
        elif rsi_val < 50 and prev.get("RSI", 50) > 50:
            score_down += 0.06
            reasons.append("RSI crossed below 50")

    # ── 2) MACD Histogram ──────────────────────────────────────────
    if macd_hist > 0:
        score_up += 0.12
        reasons.append("MACD hist > 0")
    elif macd_hist < 0:
        score_down += 0.12
        reasons.append("MACD hist < 0")

    # MACD histogram momentum (rising/falling)
    if macd_hist > prev_macd_hist and macd_hist > 0:
        score_up += 0.06
        reasons.append("MACD hist rising")
    elif macd_hist < prev_macd_hist and macd_hist < 0:
        score_down += 0.06
        reasons.append("MACD hist falling")

    # MACD crossover (zero line cross)
    if macd_hist > 0 and prev_macd_hist <= 0:
        score_up += 0.10
        reasons.append("MACD bullish crossover")
    elif macd_hist < 0 and prev_macd_hist >= 0:
        score_down += 0.10
        reasons.append("MACD bearish crossover")

    # ── 3) EMA Trend Alignment ─────────────────────────────────────
    if ema_trend >= 2:
        score_up += 0.18
        reasons.append("EMA fully bullish (9>21>50)")
    elif ema_trend == 1:
        score_up += 0.08
        reasons.append("EMA partially bullish")
    elif ema_trend <= -2:
        score_down += 0.18
        reasons.append("EMA fully bearish (9<21<50)")
    elif ema_trend == -1:
        score_down += 0.08
        reasons.append("EMA partially bearish")

    # Price vs EMA9 (immediate momentum)
    if close > ema9:
        score_up += 0.05
    else:
        score_down += 0.05

    # ── 4) Bollinger Bands ─────────────────────────────────────────
    # BB position: near lower = oversold, near upper = overbought
    if bb_pct_b < 0.10:
        score_up += 0.14
        reasons.append(f"Price near BB lower ({bb_pct_b:.2f})")
    elif bb_pct_b < 0.25:
        score_up += 0.06
    elif bb_pct_b > 0.90:
        score_down += 0.14
        reasons.append(f"Price near BB upper ({bb_pct_b:.2f})")
    elif bb_pct_b > 0.75:
        score_down += 0.06

    # BB squeeze breakout: BB width expanding from tight (momentum breakout)
    if bb_width > prev_bb_width * 1.2 and bb_width < 0.015:
        if bb_pct_b > 0.5:
            score_up += 0.10
            reasons.append("BB squeeze breakout UP")
        else:
            score_down += 0.10
            reasons.append("BB squeeze breakout DOWN")

    # ── 5) Stochastic Oscillator ───────────────────────────────────
    if stoch_k < 20:
        score_up += 0.10
        reasons.append(f"Stoch oversold (K={stoch_k:.1f})")
    elif stoch_k > 80:
        score_down += 0.10
        reasons.append(f"Stoch overbought (K={stoch_k:.1f})")

    # Stochastic crossover
    if stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d and stoch_k < 50:
        score_up += 0.08
        reasons.append("Stoch bullish cross (oversold zone)")
    elif stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d and stoch_k > 50:
        score_down += 0.08
        reasons.append("Stoch bearish cross (overbought zone)")

    # ── 6) ADX Trend Strength (filter / amplifier) ─────────────────
    adx_mult = 1.0
    if adx_val > 35:
        adx_mult = 1.25
        reasons.append(f"Very strong trend (ADX={adx_val:.1f})")
    elif adx_val > 25:
        adx_mult = 1.10
        reasons.append(f"Strong trend (ADX={adx_val:.1f})")
    elif adx_val < 15:
        adx_mult = 0.85  # sideways market, reduce confidence

    # ── 7) Volume Confirmation ─────────────────────────────────────
    if vol_ratio > 1.5:
        reasons.append(f"Volume spike (x{vol_ratio:.1f})")
        # Volume spike confirms direction
        if ema_trend > 0 or macd_hist > 0:
            score_up += 0.06
        elif ema_trend < 0 or macd_hist < 0:
            score_down += 0.06

    # ── 8) Candlestick Patterns ────────────────────────────────────
    if bullish_engulf:
        score_up += 0.14
        reasons.append("Bullish Engulfing pattern")
    if bearish_engulf:
        score_down += 0.14
        reasons.append("Bearish Engulfing pattern")
    if hammer:
        score_up += 0.10
        reasons.append("Hammer pattern")
    if shooting_star:
        score_down += 0.10
        reasons.append("Shooting Star pattern")

    # ── Apply ADX multiplier to directional bias ───────────────────
    dominant = max(score_up, score_down)
    if dominant > 0:
        if score_up > score_down:
            score_up = 0.5 + (score_up - score_down) * 0.5 * adx_mult
            score_down = 1.0 - score_up
        else:
            score_down = 0.5 + (score_down - score_up) * 0.5 * adx_mult
            score_up = 1.0 - score_down

    if score_up > score_down:
        # bullish bias: normalize to (0.5, 0.95]
        strength = (score_up - score_down) / (score_up + score_down + 1e-9)
        prob_up = 0.5 + strength * 0.45
    elif score_down > score_up:
        # bearish bias: normalize to [0.05, 0.5)
        strength = (score_down - score_up) / (score_up + score_down + 1e-9)
        prob_up = 0.5 - strength * 0.45
    else:
        prob_up = 0.5

    # Normalize
    prob_up = max(0.05, min(0.95, prob_up))
    prob_down = 1.0 - prob_up

    return {
        "prob_up": float(prob_up),
        "prob_down": float(prob_down),
        "reasons": reasons,
    }
