import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

from .config import settings

# เดิม settings.AI_LOG_PATH อาจเป็น "logs/ai_log.jsonl"
# ตรงนี้เราใช้เป็น base directory แทน
BASE_AI_LOG_DIR = os.path.dirname(settings.AI_LOG_PATH) or "logs"
LAST_STATE_PATH = settings.AI_LAST_STATE_PATH


def get_daily_log_path() -> str:
    """
    สร้าง path สำหรับไฟล์ log ประจำวัน เช่น logs/ai_log_2025-12-09.jsonl
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"ai_log_{today}.jsonl"
    return os.path.join(BASE_AI_LOG_DIR, filename)


def append_ai_log(record: Dict[str, Any]) -> None:
    """
    เขียน 1 บรรทัดลงไฟล์ log ของวันปัจจุบัน (jsonl)
    """
    path = get_daily_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_last_state(state: Dict[str, Any]) -> None:
    """
    เก็บ last_state สำหรับ Dashboard (ไฟล์เดียว)
    """
    path = LAST_STATE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
