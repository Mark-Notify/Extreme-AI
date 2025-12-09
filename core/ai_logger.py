import json
import os
from datetime import datetime
from typing import Dict, Any

from .config import settings


def ensure_log_dirs():
    os.makedirs(os.path.dirname(settings.AI_LOG_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(settings.AI_LAST_STATE_PATH), exist_ok=True)


def append_ai_log(record: Dict[str, Any]):
    ensure_log_dirs()
    record = dict(record)
    record.setdefault("timestamp", datetime.utcnow().isoformat())
    with open(settings.AI_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_last_state(state: Dict[str, Any]):
    ensure_log_dirs()
    with open(settings.AI_LAST_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
