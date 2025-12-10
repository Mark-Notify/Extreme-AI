# core/mt5_trader.py
from typing import Optional

import MetaTrader5 as mt5
from .config import settings


def execute_order(
    symbol: str,
    side: str,
    volume: float,
    sl: Optional[float] = None,
    tp: Optional[float] = None,
):
    """
    ยิงออเดอร์ทันที (market order) พร้อม SL/TP ถ้ามี
    สมมติว่า init_mt5() / login ถูกเรียกจากที่อื่นแล้ว (main หรือ dashboard)
    """
    side = side.upper()

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"error": "no_tick_info"}

    if side == "BUY":
        price = tick.ask
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        order_type = mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": float(price),
        "deviation": getattr(settings, "MT5_DEVIATION", 20),
        "magic": getattr(settings, "MT5_MAGIC_NUMBER", 123456),
        "comment": "ExtremeAI v4",
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    if sl is not None:
        request["sl"] = float(sl)
    if tp is not None:
        request["tp"] = float(tp)

    result = mt5.order_send(request)
    try:
        return result._asdict()
    except Exception:
        return {"result": str(result)}


def get_account_balance() -> float:
    """
    ดึง Balance ปัจจุบันจาก MT5
    """
    info = mt5.account_info()
    if info is None:
        return 0.0
    return float(info.balance)


def get_open_trades_count(symbol: Optional[str] = None) -> int:
    """
    นับจำนวนไม้ที่เปิดอยู่ (option: filter ตาม symbol)
    """
    orders = mt5.positions_get()
    if orders is None:
        return 0

    if symbol:
        s = symbol.upper()
        return sum(1 for pos in orders if pos.symbol.upper() == s)
    return len(orders)
