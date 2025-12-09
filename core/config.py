from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    SYMBOL: str = os.getenv("SYMBOL", "XAUUSDm")
    TIMEFRAME: str = os.getenv("TIMEFRAME", "M1")
    LOOP_INTERVAL_SEC: int = int(os.getenv("LOOP_INTERVAL_SEC", "5"))
    LOOKBACK_BARS: int = int(os.getenv("LOOKBACK_BARS", "500"))

    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")

    AUTO_TRADE_ENABLED: bool = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
    MAX_OPEN_TRADES: int = int(os.getenv("MAX_OPEN_TRADES", "3"))
    RISK_PER_TRADE: float = float(os.getenv("RISK_PER_TRADE", "0.01"))  # 1% default

    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    AI_LOG_PATH: str = os.getenv("AI_LOG_PATH", "logs/ai_log.jsonl")
    AI_LAST_STATE_PATH: str = os.getenv("AI_LAST_STATE_PATH", "logs/last_state.json")
    LSTM_MODEL_PATH: str = os.getenv("LSTM_MODEL_PATH", "models/extreme_lstm.keras")

    # ===== Manual Dashboard Volume (ปุ่ม BUY/SELL/AUTO ที่ Dashboard ใช้ตัวนี้) =====
    MANUAL_TRADE_VOLUME: float = float(os.getenv("MANUAL_TRADE_VOLUME", "0.10"))

    # ===== Position sizing & ATR/ADX filter =====
    ATR_SL_MULTIPLIER: float = float(os.getenv("ATR_SL_MULTIPLIER", "1.5"))   # SL = 1.5 ATR
    ATR_TP_MULTIPLIER: float = float(os.getenv("ATR_TP_MULTIPLIER", "3.0"))   # TP = 3 ATR
    ADX_TREND_THRESHOLD: float = float(os.getenv("ADX_TREND_THRESHOLD", "20.0"))

    # Tick value/size ใช้คำนวณ lot จาก risk (ต้องปรับตามบัญชีจริง)
    TICK_VALUE: float = float(os.getenv("TICK_VALUE", "1.0"))
    TICK_SIZE: float = float(os.getenv("TICK_SIZE", "0.1"))

    # min/max lot ต่อไม้
    MIN_VOLUME: float = float(os.getenv("MIN_VOLUME", "0.01"))
    MAX_VOLUME: float = float(os.getenv("MAX_VOLUME", "10.0"))


settings = Settings()
