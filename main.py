import time
from datetime import datetime, timezone

from core.config import settings
from core.data_feed import init_mt5, get_recent_ohlc
from core.indicators import add_all_indicators
from core.ai_engine import ExtremeAIEngine
from core.ai_logger import append_ai_log, write_last_state
from core.charting import generate_signal_chart
from core.mt5_trader import execute_order, get_account_balance, get_open_trades_count
from core.position_sizing import calculate_position_size
from core.trade_logger import log_trade  # ยังไม่ใช้ แต่เผื่ออนาคต
from core.trade_utils import compute_sl_tp_by_ai
from core.llm_advisor import LLMAdvisor
from core.discord_notifier import (
    notify_bot_started,
    notify_pre_signal,
    notify_confirm_signal,
    notify_trade,
    notify_error,
    notify_ai_result,
)

# เขียน log ลงไฟล์สำหรับเทรน ไม่ต้องทุก loop
AI_LOG_INTERVAL_SEC = getattr(settings, "AI_LOG_INTERVAL_SEC", 5)
LAST_AI_LOG_TS = 0.0
LAST_AI_DISCORD_TS = 0.0

# ถ้าใช้ AI Insight Panel (Rule vs LSTM + disagreement)
STATS_AI = {
    "total_samples": 0,
    "disagree_samples": 0,
}


def classify_zone(rsi_value: float) -> str:
    if rsi_value < 30:
        return "Oversold"
    if rsi_value > 70:
        return "Overbought"
    return "Neutral"


def is_session_active() -> bool:
    """
    ตรวจสอบว่าตอนนี้อยู่ใน Session ที่กำหนดหรือไม่ (UTC)
    SESSION_ACTIVE_HOURS = "07:00-17:00" → เทรดเฉพาะช่วง London + NY open
    """
    if not getattr(settings, "SESSION_FILTER_ENABLED", False):
        return True

    hours_str = getattr(settings, "SESSION_ACTIVE_HOURS", "07:00-17:00")
    try:
        start_str, end_str = hours_str.split("-")
        sh, sm = int(start_str.split(":")[0]), int(start_str.split(":")[1])
        eh, em = int(end_str.split(":")[0]), int(end_str.split(":")[1])
        now_utc = datetime.now(timezone.utc)
        now_min = now_utc.hour * 60 + now_utc.minute
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        return start_min <= now_min < end_min
    except Exception:
        return True


def count_confirm_factors(last, ai_res: dict, confirm_side: str) -> int:
    """
    นับจำนวน confirmation factors ที่สนับสนุนทิศทางที่ต้องการ
    ใช้กรอง False Signal เพิ่มเติม (ต้องผ่านอย่างน้อย MIN_CONFIRM_FACTORS)

    Factors:
    1. EMA trend aligned with signal
    2. Bollinger Band position supports signal
    3. Stochastic supports signal (oversold/overbought)
    4. Volume spike (VOL_RATIO > 1.3)
    5. Candlestick pattern confirms
    """
    count = 0
    side = confirm_side.upper()

    ema_trend = float(last.get("EMA_TREND", 0))
    bb_pct_b = float(last.get("BB_PCT_B", 0.5))
    stoch_k = float(last.get("STOCH_K", 50))
    vol_ratio = float(last.get("VOL_RATIO", 1.0))
    bullish_engulf = int(last.get("BULLISH_ENGULF", 0))
    bearish_engulf = int(last.get("BEARISH_ENGULF", 0))
    hammer = int(last.get("HAMMER", 0))
    shooting_star = int(last.get("SHOOTING_STAR", 0))

    if side == "BUY":
        if ema_trend >= 1:
            count += 1
        if bb_pct_b < 0.35:
            count += 1
        if stoch_k < 40:
            count += 1
        if bullish_engulf or hammer:
            count += 1
    else:  # SELL
        if ema_trend <= -1:
            count += 1
        if bb_pct_b > 0.65:
            count += 1
        if stoch_k > 60:
            count += 1
        if bearish_engulf or shooting_star:
            count += 1

    # Volume spike always counts
    if vol_ratio > 1.3:
        count += 1

    return count


def main_loop():
    global LAST_AI_LOG_TS, LAST_AI_DISCORD_TS

    print("[ExtremeAI v4] starting...")
    init_mt5()
    notify_bot_started()
    engine = ExtremeAIEngine()
    llm_advisor = LLMAdvisor()

    while True:
        # ใช้ timezone-aware datetime ป้องกัน warning
        loop_started = datetime.now(timezone.utc).isoformat()

        try:
            # 0) Session filter
            if not is_session_active():
                time.sleep(settings.LOOP_INTERVAL_SEC)
                continue

            # 1) ดึงข้อมูลราคา / OHLC
            df_raw = get_recent_ohlc(
                settings.SYMBOL,
                settings.TIMEFRAME,
                settings.LOOKBACK_BARS,
            )
            if df_raw is None or df_raw.empty:
                print("[LOOP] no data, skip")
                time.sleep(settings.LOOP_INTERVAL_SEC)
                continue

            # 2) คำนวณ Indicators (RSI, MACD, ATR, ADX, EMA, BB, Stoch, Volume, Patterns)
            df = add_all_indicators(df_raw)
            if df.empty:
                print("[LOOP] indicators empty")
                time.sleep(settings.LOOP_INTERVAL_SEC)
                continue

            # 3) คำนวณ AI (Rule + LSTM)
            ai_res = engine.compute_ai(df)
            last = df.iloc[-1]

            # --- แยกค่า rule / lstm (ถ้ามี) สำหรับ AI Insight ---
            prob_up_rule = float(ai_res.get("prob_up_rule", ai_res["prob_up"]))
            prob_up_lstm = ai_res.get("prob_up_lstm")
            dir_rule = ai_res.get("direction_rule")
            dir_lstm = ai_res.get("direction_lstm")

            disagree_rate = None
            if ai_res.get("use_lstm") and dir_rule and dir_lstm:
                STATS_AI["total_samples"] += 1
                if dir_rule != dir_lstm:
                    STATS_AI["disagree_samples"] += 1
                if STATS_AI["total_samples"]:
                    disagree_rate = (
                        STATS_AI["disagree_samples"] / STATS_AI["total_samples"]
                    )

            # --- ค่า indicator หลัก ---
            rsi_val = float(last["RSI"])
            zone = classify_zone(rsi_val)
            macd_hist = float(last["MACD_HIST"])
            price = float(last["Close"])
            atr_val = float(last["ATR"])
            adx_val = float(last["ADX"])

            # --- ค่า indicator ใหม่ ---
            ema_trend = float(last.get("EMA_TREND", 0))
            bb_pct_b = float(last.get("BB_PCT_B", 0.5))
            bb_width = float(last.get("BB_WIDTH", 0))
            stoch_k = float(last.get("STOCH_K", 50))
            vol_ratio = float(last.get("VOL_RATIO", 1.0))

            prob_up = float(ai_res["prob_up"])
            prob_down = float(ai_res["prob_down"])
            regime = ai_res["regime"]
            confidence = float(ai_res["confidence"])

            # Rule-based reasons (for LLM context)
            rule_reasons = ai_res.get("rule_based", {}).get("reasons", [])

            # 4) เงื่อนไข PRE-SIGNAL (ใช้ multi-factor)
            pre = None
            pre_score = 0
            if zone in ("Oversold", "Overbought"):
                pre_score += 1
            if abs(macd_hist) > 0.15:
                pre_score += 1
            if confidence > 0.55:
                pre_score += 1
            if abs(ema_trend) >= 1:
                pre_score += 1
            if bb_pct_b < 0.20 or bb_pct_b > 0.80:
                pre_score += 1

            if pre_score >= 2:
                pre = {
                    "type": "PRE",
                    "side_hint": "BUY" if prob_up > prob_down else "SELL",
                    "score": pre_score,
                }

            # 5) เงื่อนไข CONFIRM-SIGNAL (เลือกตาม AI_MODE)
            th_up, th_down, th_conf, macd_margin = get_ai_confirm_thresholds()
            min_factors = getattr(settings, "MIN_CONFIRM_FACTORS", 2)

            confirm = None
            # BUY: prob_up สูงพอ, MACD ไม่สวนแรงลง, confidence ถึง
            if prob_up > th_up and macd_hist > -macd_margin and confidence > th_conf:
                factors = count_confirm_factors(last, ai_res, "BUY")
                if factors >= min_factors:
                    confirm = {"type": "CONFIRM", "side": "BUY", "factors": factors}
            # SELL: prob_down สูงพอ, MACD ไม่สวนแรงขึ้น, confidence ถึง
            elif prob_down > th_down and macd_hist < macd_margin and confidence > th_conf:
                factors = count_confirm_factors(last, ai_res, "SELL")
                if factors >= min_factors:
                    confirm = {"type": "CONFIRM", "side": "SELL", "factors": factors}

            pre_ts = None
            confirm_ts = None

            # 5b) สร้างกราฟสัญญาณ (ถ้ามี PRE หรือ CONFIRM)
            chart_path = None
            if pre or confirm:
                idx_last = len(df) - 1
                pre_idx = idx_last if pre else None
                confirm_idx = idx_last if confirm else None
                try:
                    chart_path = generate_signal_chart(df, pre_idx, confirm_idx)
                except Exception:
                    chart_path = None

            # 6) PRE notify
            if pre:
                msg = (
                    f"Symbol: {settings.SYMBOL}\n"
                    f"Price: {price}\n"
                    f"AI Prob Up: {prob_up:.2%} / Down: {prob_down:.2%}\n"
                    f"RSI: {rsi_val:.2f} ({zone})\n"
                    f"MACD Hist: {macd_hist:.4f}\n"
                    f"EMA Trend: {int(ema_trend):+d}\n"
                    f"BB %B: {bb_pct_b:.2f}\n"
                    f"Regime: {regime}\n"
                    f"Side Hint: {pre['side_hint']}"
                )
                notify_pre_signal(msg, chart_path)
                pre_ts = loop_started

            # 7) CONFIRM notify + auto trade (พร้อม SL/TP จาก AI)
            llm_result: dict = {}
            if confirm:
                factors_str = f"Factors: {confirm['factors']}/5"
                msg = (
                    f"Symbol: {settings.SYMBOL}\n"
                    f"Price: {price}\n"
                    f"AI Direction: {confirm['side']}\n"
                    f"AI Prob Up: {prob_up:.2%} / Down: {prob_down:.2%}\n"
                    f"RSI: {rsi_val:.2f} ({zone})\n"
                    f"MACD Hist: {macd_hist:.4f}\n"
                    f"EMA Trend: {int(ema_trend):+d} | BB%B: {bb_pct_b:.2f}\n"
                    f"Stoch K: {stoch_k:.1f} | Vol: x{vol_ratio:.1f}\n"
                    f"Regime: {regime} | {factors_str}\n"
                    f"Confidence: {confidence:.2f}"
                )

                # 7a) LLM confirmation (GPT + Gemini) — ส่ง context เพิ่มขึ้น
                market_snapshot = {
                    "symbol": settings.SYMBOL,
                    "price": price,
                    "rsi": rsi_val,
                    "rsi_zone": zone,
                    "macd_hist": macd_hist,
                    "atr": atr_val,
                    "adx": adx_val,
                    "regime": regime,
                    "ai_prob_up": prob_up,
                    "ai_prob_down": prob_down,
                    "ai_confidence": confidence,
                    "ai_direction": ai_res["direction"],
                    # New context fields
                    "ema_trend": ema_trend,
                    "bb_pct_b": bb_pct_b,
                    "bb_width": bb_width,
                    "stoch_k": stoch_k,
                    "vol_ratio": vol_ratio,
                    "rule_reasons": rule_reasons,
                }
                llm_result = llm_advisor.analyze_signal(market_snapshot, confirm["side"])

                # ถ้าเปิด LLM_REQUIRE_CONSENSUS → ต้องให้ LLM เห็นด้วยถึงจะส่ง notify
                llm_blocks = (
                    settings.LLM_REQUIRE_CONSENSUS
                    and settings.LLM_ADVISOR_ENABLED
                    and not llm_result.get("llm_agrees", True)
                )
                if not llm_blocks:
                    notify_confirm_signal(msg, chart_path)
                    confirm_ts = loop_started
                else:
                    print(
                        f"[LLM] BLOCKED trade {confirm['side']} — "
                        f"LLM consensus={llm_result.get('consensus')} "
                        f"(conf={llm_result.get('consensus_confidence', 0):.2f})"
                    )

                if settings.AUTO_TRADE_ENABLED and not llm_blocks:
                    # 7b) ตรวจ MAX_OPEN_TRADES ก่อนเปิดไม้ใหม่
                    open_count = get_open_trades_count(settings.SYMBOL)
                    if open_count >= settings.MAX_OPEN_TRADES:
                        print(
                            f"[LOOP] MAX_OPEN_TRADES reached ({open_count}/{settings.MAX_OPEN_TRADES}), skipping"
                        )
                    else:
                        # 7c) Dynamic position sizing ตาม account balance + ATR
                        account_balance = get_account_balance()
                        volume = calculate_position_size(
                            balance=account_balance,
                            atr=atr_val,
                            risk_percent=settings.RISK_PER_TRADE,
                        )

                        # 7d) ให้ AI ช่วยคิด SL/TP (ใช้ bb_width + adx เพิ่มเติม)
                        sl_price, tp_price = compute_sl_tp_by_ai(
                            entry_price=price,
                            side=confirm["side"],
                            atr=atr_val,
                            regime=regime,
                            confidence=confidence,
                            bb_width=bb_width,
                            adx=adx_val,
                        )

                        trade_result = execute_order(
                            settings.SYMBOL,
                            confirm["side"],
                            volume,
                            sl=sl_price,
                            tp=tp_price,
                        )

                        notify_trade(
                            f"{confirm['side']} {volume} {settings.SYMBOL}\n"
                            f"SL={sl_price:.2f} TP={tp_price:.2f}\n"
                            f"Result: {trade_result}"
                        )

            # 8) ดึง Balance ปัจจุบันจาก MT5 (แสดงบน Dashboard)
            account_balance = get_account_balance()
            open_trades_count = get_open_trades_count(settings.SYMBOL)

            # 9) AI log line (สำหรับเทรน LSTM — ไม่ต้องเขียนทุก loop)
            log_record = {
                "symbol": settings.SYMBOL,
                "time": str(df["time"].iloc[-1]),
                "close": price,
                "rsi": rsi_val,
                "macd_hist": macd_hist,
                "atr": atr_val,
                "adx": adx_val,
                "ema_trend": ema_trend,
                "bb_pct_b": bb_pct_b,
                "bb_width": bb_width,
                "stoch_k": stoch_k,
                "vol_ratio": vol_ratio,
                "ret": float(last["RET"]),
                "ai_prob_up": prob_up,
                "ai_prob_down": prob_down,
                "ai_direction": ai_res["direction"],
                "ai_confidence": confidence,
                "regime": regime,
                "pre_signal": bool(pre),
                "confirm_signal": bool(confirm),
            }

            now_ts = time.time()
            if now_ts - LAST_AI_LOG_TS >= AI_LOG_INTERVAL_SEC:
                append_ai_log(log_record)
                LAST_AI_LOG_TS = now_ts

            # 9b) ส่งผล AI ไปยัง Discord (rate-limited ตาม AI_LOG_INTERVAL_SEC)
            if now_ts - LAST_AI_DISCORD_TS >= AI_LOG_INTERVAL_SEC:
                ai_msg = (
                    f"Symbol: {settings.SYMBOL}\n"
                    f"Price: {price:.2f}\n"
                    f"AI Direction: {ai_res['direction']}\n"
                    f"Prob Up: {prob_up:.2%} / Down: {prob_down:.2%}\n"
                    f"Confidence: {confidence:.2f}\n"
                    f"Regime: {regime}\n"
                    f"RSI: {rsi_val:.2f} ({zone}) | MACD: {macd_hist:.4f}\n"
                    f"EMA Trend: {int(ema_trend):+d} | BB%B: {bb_pct_b:.2f}\n"
                    f"Stoch K: {stoch_k:.1f} | Vol: x{vol_ratio:.1f}"
                )
                notify_ai_result(ai_msg)
                LAST_AI_DISCORD_TS = now_ts

            # 10) last_state สำหรับ Dashboard / WebSocket (อัปเดตทุก loop)
            last_state = {
                "loop_started": loop_started,
                "symbol": settings.SYMBOL,
                "timeframe": settings.TIMEFRAME,
                "price": price,
                "rsi": rsi_val,
                "rsi_zone": zone,
                "macd_hist": macd_hist,
                "atr": atr_val,
                "adx": adx_val,
                "ema_trend": ema_trend,
                "bb_pct_b": bb_pct_b,
                "bb_width": bb_width,
                "stoch_k": stoch_k,
                "vol_ratio": vol_ratio,
                "ai_prob_up": prob_up,
                "ai_prob_down": prob_down,
                "ai_direction": ai_res["direction"],
                "ai_confidence": confidence,
                "regime": regime,
                "use_lstm": ai_res.get("use_lstm", False),
                "pre_signal": pre is not None,
                "confirm_signal": confirm is not None,
                "pre_timestamp": pre_ts,
                "confirm_timestamp": confirm_ts,
                "open_trades": open_trades_count,
                "account_balance": account_balance,
                # AI Insight (Rule vs LSTM + disagreement)
                "ai_prob_rule": prob_up_rule,
                "ai_prob_lstm": prob_up_lstm,
                "ai_disagree_rate": disagree_rate,
                "ai_samples": STATS_AI["total_samples"],
                "ai_disagree_samples": STATS_AI["disagree_samples"],
                # LLM Advisor output (latest CONFIRM signal)
                "llm_consensus": llm_result.get("consensus"),
                "llm_consensus_confidence": llm_result.get("consensus_confidence"),
                "llm_agrees": llm_result.get("llm_agrees"),
                "llm_gpt_rec": llm_result.get("gpt_recommendation"),
                "llm_gpt_confidence": llm_result.get("gpt_confidence"),
                "llm_gpt_reasoning": llm_result.get("gpt_reasoning"),
                "llm_gemini_rec": llm_result.get("gemini_recommendation"),
                "llm_gemini_confidence": llm_result.get("gemini_confidence"),
                "llm_gemini_reasoning": llm_result.get("gemini_reasoning"),
            }
            write_last_state(last_state)

            print(
                f"[LOOP] {settings.SYMBOL} price={price:.2f} "
                f"AI dir={ai_res['direction']} up={prob_up:.2%} "
                f"regime={regime} EMA={int(ema_trend):+d} BB%B={bb_pct_b:.2f}"
            )

        except KeyboardInterrupt:
            print("\n[ExtremeAI v4] stopped by user.")
            break
        except Exception as e:
            print("[LOOP][ERROR]", e)
            notify_error(str(e))

        # ให้ loop วิ่งตาม config (ตั้งใน .env = 1)
        time.sleep(settings.LOOP_INTERVAL_SEC)

def get_ai_confirm_thresholds():
    """
    คืนค่า (th_up, th_down, th_conf, macd_margin) ตาม AI_MODE

    SAFE        : ยิงน้อยมาก เน้นชัวร์
    NORMAL      : กลาง ๆ
    AGGRESSIVE  : ยิงบ่อยขึ้น เน้นตามตลาดเร็ว
    """
    mode = getattr(settings, "AI_MODE", "NORMAL").upper()

    if mode == "SAFE":
        th_up = 0.65
        th_down = 0.65
        th_conf = 0.60
        macd_margin = 0.00
    elif mode == "AGGRESSIVE":
        th_up = 0.53
        th_down = 0.53
        th_conf = 0.35
        macd_margin = 0.07
    else:  # NORMAL
        th_up = 0.58
        th_down = 0.58
        th_conf = 0.45
        macd_margin = 0.03

    return th_up, th_down, th_conf, macd_margin


if __name__ == "__main__":
    main_loop()
