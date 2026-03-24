# core/trade_utils.py
"""
Shared trading utility functions used by both main.py and dashboard/server.py.
"""


def compute_sl_tp_by_ai(
    entry_price: float,
    side: str,
    atr: float,
    regime: str,
    confidence: float,
    bb_width: float = 0.0,
    adx: float = 0.0,
) -> "tuple[float, float]":
    """
    ให้ AI ช่วยคิด SL/TP จาก ATR + regime + confidence + BB width + ADX

    Dynamic Risk:Reward matrix:
    - trending + high confidence → RR 1:2.5 (ตามเทรนด์ต่อ)
    - trending + medium confidence → RR 1:2.0
    - reversal + high confidence → RR 1:2.0 (กลับตัว)
    - volatile → RR 1:1.5 + SL กว้างขึ้น (ป้องกัน whipsaw)
    - sideways → RR 1:1.4 + SL แคบ (ตลาดกรอบ)

    side: "BUY" / "SELL"
    return: (sl_price, tp_price)
    """
    atr = max(float(atr), 0.01)
    confidence = max(0.0, min(1.0, float(confidence)))

    # ── Base SL multiplier ────────────────────────────────────────────
    if regime == "volatile":
        # ตลาด volatile → SL กว้างขึ้นป้องกันถูก stop ก่อนเวลา
        atr_mult_sl = 2.2
        rr = 1.5
    elif regime == "trending":
        if confidence > 0.7:
            atr_mult_sl = 1.8
            rr = 2.5
        elif confidence > 0.5:
            atr_mult_sl = 1.6
            rr = 2.0
        else:
            atr_mult_sl = 1.4
            rr = 1.8
    elif regime == "reversal":
        if confidence > 0.65:
            atr_mult_sl = 1.5
            rr = 2.0
        else:
            atr_mult_sl = 1.3
            rr = 1.6
    else:  # sideways / unknown
        atr_mult_sl = 1.2
        rr = 1.4

    # ── ADX boost: ADX สูง → เทรนด์แข็ง → TP ไกลขึ้น ─────────────────
    if adx > 35:
        rr += 0.3
    elif adx > 25:
        rr += 0.15

    # BB squeeze: ถ้า BB width แคบ (กำลัง breakout) → TP ไกลขึ้น
    # 0.008 = ~0.8% ของราคา (เช่น XAUUSD 2000 → BB width < 16 USD ถือว่า squeeze)
    # ปรับค่านี้ตาม symbol ถ้าใช้ instrument อื่น
    if 0 < bb_width < 0.008:
        rr += 0.2

    # ── Confidence fine-tune: confidence ต่ำ → ลด RR นิดหน่อย ─────────
    if confidence < 0.4:
        rr = max(1.0, rr - 0.3)
    elif confidence > 0.8:
        rr = min(3.5, rr + 0.2)

    # ── คำนวณ SL/TP distance ──────────────────────────────────────────
    sl_dist = atr * atr_mult_sl
    tp_dist = sl_dist * rr

    side = side.upper()
    if side == "BUY":
        sl_price = entry_price - sl_dist
        tp_price = entry_price + tp_dist
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - tp_dist

    sl_price = max(sl_price, 0.01)
    tp_price = max(tp_price, 0.01)

    return round(sl_price, 2), round(tp_price, 2)


def compute_breakeven_level(
    entry_price: float,
    side: str,
    atr: float,
    move_after_atr_mult: float = 1.0,
) -> float:
    """
    คำนวณระดับ Breakeven (จุดขยับ SL มาที่ทุน + spread buffer)
    ใช้ตอนราคาวิ่งไปแล้ว move_after_atr_mult * ATR
    """
    atr = max(float(atr), 0.01)
    if side.upper() == "BUY":
        return round(entry_price + atr * move_after_atr_mult, 2)
    else:
        return round(entry_price - atr * move_after_atr_mult, 2)
