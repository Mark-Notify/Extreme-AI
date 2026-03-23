from dataclasses import dataclass, field
import os
from dotenv import load_dotenv

load_dotenv()


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).lower() == "true"


def _str(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass
class Settings:
    # Trading parameters
    SYMBOL: str = field(default_factory=lambda: _str("SYMBOL", "XAUUSDm"))
    TIMEFRAME: str = field(default_factory=lambda: _str("TIMEFRAME", "M1"))
    LOOP_INTERVAL_SEC: int = field(default_factory=lambda: _int("LOOP_INTERVAL_SEC", 5))
    AI_LOG_INTERVAL_SEC: int = field(default_factory=lambda: _int("AI_LOG_INTERVAL_SEC", 5))
    DASHBOARD_REFRESH_SEC: int = field(default_factory=lambda: _int("DASHBOARD_REFRESH_SEC", 5))
    LOOKBACK_BARS: int = field(default_factory=lambda: _int("LOOKBACK_BARS", 500))

    # MT5 Connection
    MT5_SERVER: str = field(default_factory=lambda: _str("MT5_SERVER", ""))
    MT5_LOGIN: int = field(default_factory=lambda: _int("MT5_LOGIN", 0))
    MT5_PASSWORD: str = field(default_factory=lambda: _str("MT5_PASSWORD", ""))
    MT5_DEVIATION: int = field(default_factory=lambda: _int("MT5_DEVIATION", 20))
    MT5_MAGIC_NUMBER: int = field(default_factory=lambda: _int("MT5_MAGIC_NUMBER", 123456))

    # ---- AI Confirm thresholds (ปรับจาก .env ได้) ----
    AI_CONFIRM_PROB_UP_THRESHOLD: float = field(default_factory=lambda: _float("AI_CONFIRM_PROB_UP_THRESHOLD", 0.65))
    AI_CONFIRM_PROB_DOWN_THRESHOLD: float = field(default_factory=lambda: _float("AI_CONFIRM_PROB_DOWN_THRESHOLD", 0.65))
    AI_CONFIRM_CONFIDENCE_THRESHOLD: float = field(default_factory=lambda: _float("AI_CONFIRM_CONFIDENCE_THRESHOLD", 0.60))
    AI_CONFIRM_MACD_MARGIN: float = field(default_factory=lambda: _float("AI_CONFIRM_MACD_MARGIN", 0.00))
    AI_MODE: str = field(default_factory=lambda: _str("AI_MODE", "NORMAL"))  # 🟢 SAFE / 🟡 NORMAL / 🔴 AGGRESSIVE

    # AI probability amplification factor (higher = more aggressive signal separation)
    AI_AMPLIFY_FACTOR: float = field(default_factory=lambda: _float("AI_AMPLIFY_FACTOR", 3.0))

    # Auto Trading
    AUTO_TRADE_ENABLED: bool = field(default_factory=lambda: _bool("AUTO_TRADE_ENABLED", False))
    MAX_OPEN_TRADES: int = field(default_factory=lambda: _int("MAX_OPEN_TRADES", 3))
    RISK_PER_TRADE: float = field(default_factory=lambda: _float("RISK_PER_TRADE", 0.01))
    AUTO_TRADE_VOLUME: float = field(default_factory=lambda: _float("AUTO_TRADE_VOLUME", 0.01))

    # Notifications
    DISCORD_WEBHOOK_URL: str = field(default_factory=lambda: _str("DISCORD_WEBHOOK_URL", ""))

    # File paths
    AI_LOG_PATH: str = field(default_factory=lambda: _str("AI_LOG_PATH", "logs/ai_log.jsonl"))
    AI_LAST_STATE_PATH: str = field(default_factory=lambda: _str("AI_LAST_STATE_PATH", "logs/last_state.json"))
    LSTM_MODEL_PATH: str = field(default_factory=lambda: _str("LSTM_MODEL_PATH", "models/extreme_lstm.keras"))

    # Manual trading volume
    MANUAL_TRADE_VOLUME: float = field(default_factory=lambda: _float("MANUAL_TRADE_VOLUME", 0.10))

    # Position sizing & technical indicators
    ATR_SL_MULTIPLIER: float = field(default_factory=lambda: _float("ATR_SL_MULTIPLIER", 1.5))
    ATR_TP_MULTIPLIER: float = field(default_factory=lambda: _float("ATR_TP_MULTIPLIER", 3.0))
    ADX_TREND_THRESHOLD: float = field(default_factory=lambda: _float("ADX_TREND_THRESHOLD", 20.0))

    # Tick configuration
    TICK_VALUE: float = field(default_factory=lambda: _float("TICK_VALUE", 1.0))
    TICK_SIZE: float = field(default_factory=lambda: _float("TICK_SIZE", 0.1))

    # Volume limits
    MIN_VOLUME: float = field(default_factory=lambda: _float("MIN_VOLUME", 0.01))
    MAX_VOLUME: float = field(default_factory=lambda: _float("MAX_VOLUME", 10.0))

    # LLM (GPT + Gemini) integration
    OPENAI_API_KEY: str = field(default_factory=lambda: _str("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = field(default_factory=lambda: _str("OPENAI_MODEL", "gpt-4o-mini"))
    GEMINI_API_KEY: str = field(default_factory=lambda: _str("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = field(default_factory=lambda: _str("GEMINI_MODEL", "gemini-1.5-flash"))
    LLM_ADVISOR_ENABLED: bool = field(default_factory=lambda: _bool("LLM_ADVISOR_ENABLED", False))
    LLM_REQUIRE_CONSENSUS: bool = field(default_factory=lambda: _bool("LLM_REQUIRE_CONSENSUS", False))


settings = Settings()
