# core/mt5_trader.py

import MetaTrader5 as mt5
from .config import settings


def init_mt5() -> bool:
    if not mt5.initialize():
        print("[MT5] initialize() failed")
        return False

    if settings.MT5_LOGIN and settings.MT5_PASSWORD and settings.MT5_SERVER:
        authorized = mt5.login(
            settings.MT5_LOGIN,
            password=settings.MT5_PASSWORD,
            server=settings.MT5_SERVER,
        )
        if not authorized:
            print("[MT5] login() failed, error:", mt5.last_error())
            return False

    print("[MT5] connected")
    return True

def get_account_balance() -> float:
    """
    ดึง Balance ปัจจุบันจาก MT5
    """
    info = mt5.account_info()
    if info is None:
        # เผื่อหลุด connection จะได้ไม่ error
        return 0.0
    return float(info.balance)

def get_open_trades_count(symbol: str | None = None) -> int:
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()

    if positions is None:
        return 0
    return len(positions)


def execute_order(
    symbol: str,
    side: str,
    volume: float,
    sl_price: float | None = None,
    tp_price: float | None = None,
):
    """
    ส่งคำสั่งเทรด:
    - side: BUY / SELL
    - volume: lot
    - sl_price / tp_price: ราคา SL/TP (optional)
    """

    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"Invalid side: {side}")

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise RuntimeError(f"symbol_info({symbol}) is None")

    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"symbol_info_tick({symbol}) is None")

    if side == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": float(price),
        "deviation": 20,
        "magic": 123456,
        "comment": "ExtremeAI v4",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    if sl_price is not None:
        request["sl"] = float(sl_price)
    if tp_price is not None:
        request["tp"] = float(tp_price)

    result = mt5.order_send(request)
    if result is None:
        print("[MT5] order_send() returned None")
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("[MT5] order_send() failed, retcode:", result.retcode)
    else:
        print("[MT5] order_send() OK, ticket:", result.order)

    return {
        "retcode": result.retcode,
        "order": result.order,
        "comment": result.comment,
        "price": getattr(result, "price", None),
    }
