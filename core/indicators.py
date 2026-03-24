import pandas as pd
import numpy as np


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi_val = 100 - (100 / (1 + rs))
    return pd.Series(rsi_val, index=series.index)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr_val = tr.rolling(window=period).mean()

    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr_val + 1e-9))
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr_val + 1e-9))
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
    adx_val = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx_val


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()


def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
    """
    คำนวณ Bollinger Bands
    คืนค่า: (upper, middle, lower, bb_width, bb_pct_b)
    """
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    bb_width = (upper - lower) / (middle + 1e-9)
    bb_pct_b = (series - lower) / (upper - lower + 1e-9)
    return upper, middle, lower, bb_width, bb_pct_b


def volume_ma(series: pd.Series, period: int = 20) -> pd.Series:
    """Volume moving average"""
    return series.rolling(period).mean()


def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    """
    Stochastic Oscillator (%K และ %D)
    """
    high_roll = df["High"].rolling(k_period).max()
    low_roll = df["Low"].rolling(k_period).min()
    pct_k = 100 * (df["Close"] - low_roll) / (high_roll - low_roll + 1e-9)
    pct_d = pct_k.rolling(d_period).mean()
    return pct_k, pct_d


def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    ตรวจจับรูปแบบแท่งเทียนสำคัญ:
    - BULLISH_ENGULFING: สัญญาณกลับตัวขาขึ้น
    - BEARISH_ENGULFING: สัญญาณกลับตัวขาลง
    - HAMMER: สัญญาณขาขึ้น (แท่งขาที่ล่างยาว)
    - SHOOTING_STAR: สัญญาณขาลง (แท่งขาที่บนยาว)
    - DOJI: สัญญาณความลังเล
    """
    df = df.copy()
    o = df["Open"]
    h = df["High"]
    l = df["Low"]
    c = df["Close"]

    body = (c - o).abs()
    upper_shadow = h - c.where(c > o, o)
    lower_shadow = c.where(c < o, o) - l
    candle_range = h - l + 1e-9

    prev_o = o.shift(1)
    prev_c = c.shift(1)
    prev_body = (prev_c - prev_o).abs()

    # Bullish Engulfing: แท่งปัจจุบัน bullish ครอบคลุมแท่งก่อนที่ bearish
    df["BULLISH_ENGULF"] = (
        (c > o) & (prev_c < prev_o) & (o < prev_c) & (c > prev_o)
    ).astype(int)

    # Bearish Engulfing: แท่งปัจจุบัน bearish ครอบคลุมแท่งก่อนที่ bullish
    df["BEARISH_ENGULF"] = (
        (c < o) & (prev_c > prev_o) & (o > prev_c) & (c < prev_o)
    ).astype(int)

    # Hammer: body เล็ก, lower shadow ยาว (>= 2x body), upper shadow สั้น
    df["HAMMER"] = (
        (lower_shadow >= 2 * body) &
        (upper_shadow <= 0.3 * body + 1e-9) &
        (body > 0)
    ).astype(int)

    # Shooting Star: body เล็ก, upper shadow ยาว (>= 2x body), lower shadow สั้น
    df["SHOOTING_STAR"] = (
        (upper_shadow >= 2 * body) &
        (lower_shadow <= 0.3 * body + 1e-9) &
        (body > 0)
    ).astype(int)

    # Doji: body เล็กมาก (< 10% ของ range)
    df["DOJI"] = (body < 0.1 * candle_range).astype(int)

    return df


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- Core indicators ---
    df["RSI"] = rsi(df["Close"], 14)
    macd_line, signal_line, hist = macd(df["Close"])
    df["MACD"] = macd_line
    df["MACD_SIGNAL"] = signal_line
    df["MACD_HIST"] = hist
    df["ATR"] = atr(df, 14)
    df["ADX"] = adx(df, 14)
    df["RET"] = df["Close"].pct_change()

    # --- EMA Trend System (9 / 21 / 50) ---
    df["EMA9"] = ema(df["Close"], 9)
    df["EMA21"] = ema(df["Close"], 21)
    df["EMA50"] = ema(df["Close"], 50)

    # EMA alignment score: +1 per bullish condition, -1 per bearish
    ema_bull = (df["EMA9"] > df["EMA21"]).astype(int) + (df["EMA21"] > df["EMA50"]).astype(int)
    ema_bear = (df["EMA9"] < df["EMA21"]).astype(int) + (df["EMA21"] < df["EMA50"]).astype(int)
    df["EMA_TREND"] = ema_bull - ema_bear  # range: -2 to +2

    # --- Bollinger Bands (20, 2σ) ---
    upper, middle, lower, bb_width, bb_pct_b = bollinger_bands(df["Close"], 20, 2.0)
    df["BB_UPPER"] = upper
    df["BB_MIDDLE"] = middle
    df["BB_LOWER"] = lower
    df["BB_WIDTH"] = bb_width        # ความกว้าง: สูง = volatile, ต่ำ = squeeze
    df["BB_PCT_B"] = bb_pct_b        # 0 = แตะ lower, 1 = แตะ upper, 0.5 = กลาง

    # --- Stochastic (14, 3) ---
    stoch_k, stoch_d = stochastic(df, 14, 3)
    df["STOCH_K"] = stoch_k
    df["STOCH_D"] = stoch_d

    # --- Volume MA ---
    df["VOL_MA20"] = volume_ma(df["Volume"], 20)
    df["VOL_RATIO"] = df["Volume"] / (df["VOL_MA20"] + 1e-9)  # > 1.5 = volume spike

    # --- Candlestick Patterns ---
    df = detect_candlestick_patterns(df)

    df.dropna(inplace=True)
    return df
