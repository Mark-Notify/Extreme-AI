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
) -> "tuple[float, float]":
    """
    ให้ AI ช่วยคิด SL/TP จาก ATR + regime + confidence

    side: "BUY" / "SELL"
    return: (sl_price, tp_price)
    """
    atr = max(float(atr), 0.01)

    atr_mult_sl = 1.5
    rr = 1.8

    if regime == "trending" and confidence > 0.7:
        atr_mult_sl = 1.8
        rr = 2.3
    elif regime == "sideways":
        atr_mult_sl = 1.2
        rr = 1.4

    if confidence < 0.4:
        rr = max(1.0, rr - 0.4)

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
    return sl_price, tp_price
