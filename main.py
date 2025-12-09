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
from core.trade_logger import log_trade
from core.discord_notifier import (
    notify_bot_started,
    notify_trade,
    notify_error,
)


def classify_zone(rsi_value: float) -> str:
    if rsi_value < 30:
        return "Oversold"
    if rsi_value > 70:
        return "Overbought"
    return "Neutral"


def main_loop():
    print("[ExtremeAI v4] starting...")
    if not init_mt5():
        print("[MAIN] MT5 init failed, exit.")
        return

    notify_bot_started()
    engine = ExtremeAIEngine()

    while True:
        loop_started = datetime.now(timezone.utc).isoformat()

        try:
            df_raw = get_recent_ohlc(
                settings.SYMBOL,
                settings.TIMEFRAME,
                settings.LOOKBACK_BARS,
            )
            if df_raw is None or df_raw.empty:
                print("[LOOP] no data, skip")
                time.sleep(settings.LOOP_INTERVAL_SEC)
                continue

            df = add_all_indicators(df_raw)
            if df.empty:
                print("[LOOP] indicators empty")
                time.sleep(settings.LOOP_INTERVAL_SEC)
                continue

            ai_res = engine.compute_ai(df)
            last = df.iloc[-1]

            rsi_val = float(last["RSI"])
            zone = classify_zone(rsi_val)
            macd_hist = float(last["MACD_HIST"])
            price = float(last["Close"])
            atr_val = float(last["ATR"])
            adx_val = float(last["ADX"])

            prob_up = ai_res["prob_up"]
            prob_down = ai_res["prob_down"]
            regime = ai_res["regime"]
            confidence = ai_res["confidence"]

            # PRE-SIGNAL conditions (ใช้แค่แจ้งใน dashboard / log)
            pre = None
            if zone in ("Oversold", "Overbought") or abs(macd_hist) > 0.2 or confidence > 0.6:
                pre = {
                    "type": "PRE",
                    "side_hint": "BUY" if prob_up > prob_down else "SELL",
                }

            # CONFIRM-SIGNAL conditions (เข้มขึ้นหน่อย)
            confirm = None
            confirm_side = None
            # ใช้ threshold สูงขึ้นหน่อยให้คัดไม้เนียน ๆ
            if prob_up > 0.70 and macd_hist > 0 and confidence > 0.6:
                confirm = {"type": "CONFIRM", "side": "BUY"}
                confirm_side = "BUY"
            elif prob_down > 0.70 and macd_hist < 0 and confidence > 0.6:
                confirm = {"type": "CONFIRM", "side": "SELL"}
                confirm_side = "SELL"

            pre_ts = loop_started if pre else None
            confirm_ts = loop_started if confirm else None

            chart_path = None
            if pre or confirm:
                idx_last = len(df) - 1
                pre_idx = idx_last if pre else None
                confirm_idx = idx_last if confirm else None
                # ถ้าอยากเก็บรูปไว้ดูย้อนหลัง เปิดบรรทัดนี้
                # chart_path = generate_signal_chart(df, pre_idx, confirm_idx)

            # ========== AUTO TRADE LOGIC ==========
            auto_trade_executed = False
            trade_result = None
            sl_price = None
            tp_price = None
            volume = None

            if confirm and settings.AUTO_TRADE_ENABLED and confirm_side in ("BUY", "SELL"):
                # 1) ฟิลเตอร์ ADX → ถ้าไม่มีเทรนด์ ไม่เทรด
                if adx_val < settings.ADX_TREND_THRESHOLD:
                    print(f"[AUTO] skip trade: ADX {adx_val:.2f} < {settings.ADX_TREND_THRESHOLD}")
                else:
                    # 2) เช็กจำนวนไม้เปิดอยู่
                    open_count = get_open_trades_count(settings.SYMBOL)
                    if open_count >= settings.MAX_OPEN_TRADES:
                        print(f"[AUTO] skip trade: open_trades={open_count} >= {settings.MAX_OPEN_TRADES}")
                    else:
                        # 3) คำนวณ lot จาก risk%
                        balance = get_account_balance()
                        volume = calculate_position_size(balance, atr_val)

                        # 4) คำนวณ SL/TP จาก ATR
                        sl_dist = settings.ATR_SL_MULTIPLIER * atr_val
                        tp_dist = settings.ATR_TP_MULTIPLIER * atr_val

                        if confirm_side == "BUY":
                            sl_price = price - sl_dist
                            tp_price = price + tp_dist
                        else:
                            sl_price = price + sl_dist
                            tp_price = price - tp_dist

                        # 5) ยิงออเดอร์
                        trade_result = execute_order(
                            settings.SYMBOL,
                            confirm_side,
                            volume,
                            sl_price=sl_price,
                            tp_price=tp_price,
                        )
                        auto_trade_executed = True

                        # 6) log trade
                        log_trade(
                            {
                                "symbol": settings.SYMBOL,
                                "side": confirm_side,
                                "price": price,
                                "volume": volume,
                                "sl": sl_price,
                                "tp": tp_price,
                                "prob_up": prob_up,
                                "prob_down": prob_down,
                                "confidence": confidence,
                                "rsi": rsi_val,
                                "zone": zone,
                                "macd_hist": macd_hist,
                                "atr": atr_val,
                                "adx": adx_val,
                                "regime": regime,
                                "auto": True,
                                "retcode": trade_result.get("retcode") if trade_result else None,
                            }
                        )

                        # 7) Discord เฉพาะตอนยิงออเดอร์จริง
                        msg = (
                            f"AUTO {confirm_side} {settings.SYMBOL} {volume} lot\n"
                            f"Price: {price}\n"
                            f"SL: {sl_price} | TP: {tp_price}\n"
                            f"AI Prob Up: {prob_up:.2%} / Down: {prob_down:.2%}\n"
                            f"RSI: {rsi_val:.2f} ({zone})\n"
                            f"MACD Hist: {macd_hist:.4f}\n"
                            f"ATR: {atr_val:.3f} | ADX: {adx_val:.2f}\n"
                            f"Regime: {regime}\n"
                            f"Confidence: {confidence:.2f}\n"
                            f"Result: {trade_result}"
                        )
                        notify_trade(msg)

            # ========== AI log line (สำหรับ train LSTM) ==========
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
            append_ai_log(log_record)

            # ========== last_state สำหรับ Dashboard ==========
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
                "use_lstm": ai_res["use_lstm"],
                "pre_signal": pre is not None,
                "confirm_signal": confirm is not None,
                "pre_timestamp": pre_ts,
                "confirm_timestamp": confirm_ts,
                "open_trades": get_open_trades_count(settings.SYMBOL),
            }
            write_last_state(last_state)

            print(
                f"[LOOP] {settings.SYMBOL} price={price:.2f} "
                f"AI dir={ai_res['direction']} up={prob_up:.2%} "
                f"conf={confidence:.2f} regime={regime} ADX={adx_val:.1f}"
            )

        except KeyboardInterrupt:
            print("\n[ExtremeAI v4] stopped by user.")
            break
        except Exception as e:
            print("[LOOP][ERROR]", e)
            notify_error(str(e))

        time.sleep(settings.LOOP_INTERVAL_SEC)


if __name__ == "__main__":
    main_loop()
