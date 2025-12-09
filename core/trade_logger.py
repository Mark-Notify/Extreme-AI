# core/trade_logger.py

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

LOG_PATH = "logs/trades_log.jsonl"


def log_trade(record: Dict[str, Any]):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    record = dict(record)
    if "time" not in record:
        record["time"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
