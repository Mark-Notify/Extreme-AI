from typing import Optional
import MetaTrader5 as mt5
import pandas as pd

from .config import settings
from .stability import safe_call


@safe_call(default=False)
def init_mt5() -> bool:
    if not mt5.initialize():
        print("[MT5] initialize() failed")
        return False

    if settings.MT5_LOGIN and settings.MT5_PASSWORD and settings.MT5_SERVER:
        authorized = mt5.login(
            login=settings.MT5_LOGIN,
            password=settings.MT5_PASSWORD,
            server=settings.MT5_SERVER,
        )
        if not authorized:
            print("[MT5] login() failed")
            return False
    print("[MT5] initialized.")
    return True


@safe_call(default=None)
def get_recent_ohlc(symbol: str, timeframe: str, bars: int) -> Optional[pd.DataFrame]:
    """
    ดึงข้อมูลแท่งเทียนจาก MT5 -> pandas DataFrame
    timeframe: เช่น 'M1', 'M5', 'H1'
    """
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_M1)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    if rates is None:
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "tick_volume": "Volume",
        },
        inplace=True,
    )
    return df[["time", "Open", "High", "Low", "Close", "Volume"]]
