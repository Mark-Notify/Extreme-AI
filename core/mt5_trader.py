# core/mt5_trader.py
import sys
from typing import Optional

if sys.platform == "win32":
    import MetaTrader5 as mt5
else:
    mt5 = None  # type: ignore[assignment]

from .config import settings


def _get_filling_mode(symbol: str) -> Optional[int]:
    """
    ตรวจสอบ filling mode ที่ broker รองรับสำหรับ symbol นั้น ๆ
    MT5 filling_mode เป็น bitmask:
      1 = ORDER_FILLING_FOK
      2 = ORDER_FILLING_IOC
      4 = ORDER_FILLING_RETURN
    คืนค่า None ถ้าไม่สามารถหา filling mode ที่รองรับได้
    """
    if mt5 is None:
        return None
    info = mt5.symbol_info(symbol)
    if info is None:
        return None

    filling_mode = info.filling_mode
    if filling_mode & 1:  # FOK supported
        return mt5.ORDER_FILLING_FOK
    if filling_mode & 2:  # IOC supported
        return mt5.ORDER_FILLING_IOC
    if filling_mode & 4:  # RETURN supported
        return mt5.ORDER_FILLING_RETURN
    return None


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
    if mt5 is None:
        return {"error": "MetaTrader5 is not available on this platform"}
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

    filling_mode = _get_filling_mode(symbol)
    if filling_mode is None:
        return {"error": "unsupported_filling_mode"}

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": float(price),
        "deviation": getattr(settings, "MT5_DEVIATION", 20),
        "magic": getattr(settings, "MT5_MAGIC_NUMBER", 123456),
        "comment": "ExtremeAI v4",
        "type_filling": filling_mode,
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
    if mt5 is None:
        return 0.0
    info = mt5.account_info()
    if info is None:
        return 0.0
    return float(info.balance)


def get_open_trades_count(symbol: Optional[str] = None) -> int:
    """
    นับจำนวนไม้ที่เปิดอยู่ (option: filter ตาม symbol)
    """
    if mt5 is None:
        return 0
    orders = mt5.positions_get()
    if orders is None:
        return 0

    if symbol:
        s = symbol.upper()
        return sum(1 for pos in orders if pos.symbol.upper() == s)
    return len(orders)
