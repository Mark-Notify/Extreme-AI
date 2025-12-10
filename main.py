import time
from datetime import datetime, timezone

from core.config import settings
from core.data_feed import init_mt5, get_recent_ohlc
from core.indicators import add_all_indicators
from core.ai_engine import ExtremeAIEngine
from core.ai_logger import append_ai_log, write_last_state
from core.charting import generate_signal_chart
from core.mt5_trader import execute_order, get_account_balance, get_open_trades_count
from core.position_sizing import calculate_position_size  # ยังไม่ใช้ แต่เผื่ออนาคต
from core.trade_logger import log_trade  # ยังไม่ใช้ แต่เผื่ออนาคต
from core.discord_notifier import (
    notify_bot_started,
    notify_pre_signal,
    notify_confirm_signal,
    notify_trade,
    notify_error,
)

# เขียน log ลงไฟล์สำหรับเทรน ไม่ต้องทุก loop
AI_LOG_INTERVAL_SEC = getattr(settings, "AI_LOG_INTERVAL_SEC", 5)
LAST_AI_LOG_TS = 0.0

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


def compute_sl_tp_by_ai(
    entry_price: float,
    side: str,
    atr: float,
    regime: str,
    confidence: float,
) -> tuple[float, float]:
    """
    ให้ AI ช่วยคิด SL/TP จาก ATR + regime + confidence

    side: "BUY" / "SELL"
    return: (sl_price, tp_price)
    """
    # กันค่าแปลก ๆ
    atr = max(float(atr), 0.01)

    # --- base parameter ---
    # ระยะ SL จาก ATR
    atr_mult_sl = 1.5   # SL ≈ 1.5 * ATR
    rr = 1.8            # TP ≈ 1.8R

    # ปรับตาม regime + confidence
    if regime == "trending" and confidence > 0.7:
        atr_mult_sl = 1.8
        rr = 2.3
    elif regime == "sideways":
        atr_mult_sl = 1.2
        rr = 1.4

    # ถ้า confidence ต่ำมาก ลด RR เพื่อเก็บสั้น
    if confidence < 0.4:
        rr = max(1.0, rr - 0.4)

    sl_dist = atr * atr_mult_sl
    tp_dist = sl_dist * rr

    if side.upper() == "BUY":
        sl_price = entry_price - sl_dist
        tp_price = entry_price + tp_dist
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - tp_dist

    # กันค่าติดลบ
    sl_price = max(sl_price, 0.01)
    tp_price = max(tp_price, 0.01)
    return sl_price, tp_price


def main_loop():
    global LAST_AI_LOG_TS

    print("[ExtremeAI v4] starting...")
    init_mt5()
    notify_bot_started()
    engine = ExtremeAIEngine()

    while True:
        # ใช้ timezone-aware datetime ป้องกัน warning
        loop_started = datetime.now(timezone.utc).isoformat()

        try:
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

            # 2) คำนวณ Indicators
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

            prob_up = float(ai_res["prob_up"])
            prob_down = float(ai_res["prob_down"])
            regime = ai_res["regime"]
            confidence = float(ai_res["confidence"])

            # 4) เงื่อนไข PRE-SIGNAL
            pre = None
            if (
                zone in ("Oversold", "Overbought")
                or abs(macd_hist) > 0.2
                or confidence > 0.6
            ):
                pre = {
                    "type": "PRE",
                    "side_hint": "BUY" if prob_up > prob_down else "SELL",
                }


            # 5) เงื่อนไข CONFIRM-SIGNAL (เลือกตาม AI_MODE)
            th_up, th_down, th_conf, macd_margin = get_ai_confirm_thresholds()

            confirm = None
            # BUY: prob_up สูงพอ, MACD ไม่สวนแรงลง, confidence ถึง
            if prob_up > th_up and macd_hist > -macd_margin and confidence > th_conf:
                confirm = {"type": "CONFIRM", "side": "BUY"}
            # SELL: prob_down สูงพอ, MACD ไม่สวนแรงขึ้น, confidence ถึง
            elif prob_down > th_down and macd_hist < macd_margin and confidence > th_conf:
                confirm = {"type": "CONFIRM", "side": "SELL"}


            pre_ts = None
            confirm_ts = None

            chart_path = None
            if pre or confirm:
                # index ของแท่งล่าสุด
                idx_last = len(df) - 1
                pre_idx = idx_last if pre else None
                confirm_idx = idx_last if confirm else None
                # chart_path = generate_signal_chart(df, pre_idx, confirm_idx)
                _ = (pre_idx, confirm_idx)  # กัน warning unused ถ้าไม่ใช้ chart

            # 6) PRE notify
            if pre:
                msg = (
                    f"Symbol: {settings.SYMBOL}\n"
                    f"Price: {price}\n"
                    f"AI Prob Up: {prob_up:.2%} / Down: {prob_down:.2%}\n"
                    f"RSI: {rsi_val:.2f} ({zone})\n"
                    f"MACD Hist: {macd_hist:.4f}\n"
                    f"Regime: {regime}\n"
                    f"Side Hint: {pre['side_hint']}"
                )
                notify_pre_signal(msg, chart_path)
                pre_ts = loop_started

            # 7) CONFIRM notify + auto trade (พร้อม SL/TP จาก AI)
            if confirm:
                msg = (
                    f"Symbol: {settings.SYMBOL}\n"
                    f"Price: {price}\n"
                    f"AI Direction: {confirm['side']}\n"
                    f"AI Prob Up: {prob_up:.2%} / Down: {prob_down:.2%}\n"
                    f"RSI: {rsi_val:.2f} ({zone})\n"
                    f"MACD Hist: {macd_hist:.4f}\n"
                    f"Regime: {regime}\n"
                    f"Confidence: {confidence:.2f}"
                )
                notify_confirm_signal(msg, chart_path)
                confirm_ts = loop_started

                if settings.AUTO_TRADE_ENABLED:
                    volume = settings.AUTO_TRADE_VOLUME  # ปรับใน .env ได้

                    # ให้ AI ช่วยคิด SL/TP
                    sl_price, tp_price = compute_sl_tp_by_ai(
                        entry_price=price,
                        side=confirm["side"],
                        atr=atr_val,
                        regime=regime,
                        confidence=confidence,
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

            # 10) last_state สำหรับ Dashboard / WebSocket (อัปเดตทุก loop = ทุก 1 วิ)
            last_state = {
                "loop_started": loop_started,
                "symbol": settings.SYMBOL,
                "price": price,
                "rsi": rsi_val,
                "rsi_zone": zone,
                "macd_hist": macd_hist,
                "atr": atr_val,
                "adx": adx_val,
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

                # open trades (จำนวนไม้ของ symbol นี้)
                "open_trades": open_trades_count,

                # ✅ Balance realtime
                "account_balance": account_balance,

                # ✅ AI Insight (Rule vs LSTM + disagreement)
                "ai_prob_rule": prob_up_rule,
                "ai_prob_lstm": prob_up_lstm,
                "ai_disagree_rate": disagree_rate,
                "ai_samples": STATS_AI["total_samples"],
                "ai_disagree_samples": STATS_AI["disagree_samples"],
            }
            write_last_state(last_state)

            print(
                f"[LOOP] {settings.SYMBOL} price={price:.2f} "
                f"AI dir={ai_res['direction']} up={prob_up:.2%} regime={regime}"
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
