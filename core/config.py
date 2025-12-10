from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # Trading parameters
    SYMBOL: str = os.getenv("SYMBOL", "XAUUSDm")
    TIMEFRAME: str = os.getenv("TIMEFRAME", "M1")
    LOOP_INTERVAL_SEC: int = int(os.getenv("LOOP_INTERVAL_SEC", "5"))
    AI_LOG_INTERVAL_SEC: int = int(os.getenv("AI_LOG_INTERVAL_SEC", "5"))
    DASHBOARD_REFRESH_SEC: int = int(os.getenv("DASHBOARD_REFRESH_SEC", "5"))
    LOOKBACK_BARS: int = int(os.getenv("LOOKBACK_BARS", "500"))

    # MT5 Connection
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")

    # ---- AI Confirm thresholds (ปรับจาก .env ได้) ----
    AI_CONFIRM_PROB_UP_THRESHOLD: float = float(os.getenv("AI_CONFIRM_PROB_UP_THRESHOLD", "0.65"))
    AI_CONFIRM_PROB_DOWN_THRESHOLD: float = float(os.getenv("AI_CONFIRM_PROB_DOWN_THRESHOLD", "0.65"))
    AI_CONFIRM_CONFIDENCE_THRESHOLD: float = float(os.getenv("AI_CONFIRM_CONFIDENCE_THRESHOLD", "0.60"))
    AI_CONFIRM_MACD_MARGIN: float = float(os.getenv("AI_CONFIRM_MACD_MARGIN", "0.00"))  # ใช้ดูทิศ MACD แบบหลวม/เข้ม

    # Auto Trading
    AUTO_TRADE_ENABLED: bool = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
    MAX_OPEN_TRADES: int = int(os.getenv("MAX_OPEN_TRADES", "3"))
    RISK_PER_TRADE: float = float(os.getenv("RISK_PER_TRADE", "0.01"))

    # Notifications
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    # File paths
    AI_LOG_PATH: str = os.getenv("AI_LOG_PATH", "logs/ai_log.jsonl")
    AI_LAST_STATE_PATH: str = os.getenv("AI_LAST_STATE_PATH", "logs/last_state.json")
    LSTM_MODEL_PATH: str = os.getenv("LSTM_MODEL_PATH", "models/extreme_lstm.keras")

    # Manual trading volume
    MANUAL_TRADE_VOLUME: float = float(os.getenv("MANUAL_TRADE_VOLUME", "0.10"))

    # Position sizing & technical indicators
    ATR_SL_MULTIPLIER: float = float(os.getenv("ATR_SL_MULTIPLIER", "1.5"))
    ATR_TP_MULTIPLIER: float = float(os.getenv("ATR_TP_MULTIPLIER", "3.0"))
    ADX_TREND_THRESHOLD: float = float(os.getenv("ADX_TREND_THRESHOLD", "20.0"))

    # Tick configuration
    TICK_VALUE: float = float(os.getenv("TICK_VALUE", "1.0"))
    TICK_SIZE: float = float(os.getenv("TICK_SIZE", "0.1"))

    # Volume limits
    MIN_VOLUME: float = float(os.getenv("MIN_VOLUME", "0.01"))
    MAX_VOLUME: float = float(os.getenv("MAX_VOLUME", "10.0"))


settings = Settings()
