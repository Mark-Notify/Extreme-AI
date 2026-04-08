import json
from typing import Optional

import requests

from .config import settings


def _post(content: str, file_path: Optional[str] = None):
    if not settings.DISCORD_WEBHOOK_URL:
        return
    data = {"content": content}
    if file_path:
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                try:
                    resp = requests.post(
                        settings.DISCORD_WEBHOOK_URL,
                        data={"payload_json": json.dumps(data)},
                        files=files,
                        timeout=10,
                    )
                    if not resp.ok:
                        print("[DISCORD] error:", resp.status_code, resp.text)
                except Exception as e:
                    print("[DISCORD] exception:", e)
        except Exception as e:
            print("[DISCORD] file error:", e)
        return

    try:
        resp = requests.post(
            settings.DISCORD_WEBHOOK_URL,
            data={"payload_json": json.dumps(data)},
            timeout=10,
        )
        if not resp.ok:
            print("[DISCORD] error:", resp.status_code, resp.text)
    except Exception as e:
        print("[DISCORD] exception:", e)


def notify_bot_started():
    _post("🚀 **Extreme AI v4 Bot Started**")


def notify_pre_signal(message: str, chart_path: Optional[str] = None):
    _post("🔔 **PRE Signal**\n" + message, chart_path)


def notify_confirm_signal(message: str, chart_path: Optional[str] = None):
    _post("✅ **CONFIRM Signal**\n" + message, chart_path)


def notify_trade(message: str):
    """
    ใช้เฉพาะ 'ตอนออกออเดอร์จริง' เท่านั้น
    - Auto trade จาก main.py
    - Manual trade จาก Dashboard (BUY / SELL / AUTO)
    """
    _post("🤖 **Executed Trade**\n" + message)


def notify_ai_result(message: str):
    """
    ส่งผล AI ที่ได้แต่ละรอบไปยัง Discord
    เรียกจาก main.py โดย rate-limit ตาม AI_LOG_INTERVAL_SEC
    """
    _post("📊 **AI Result**\n" + message)


def notify_error(message: str):
    _post("⚠️ **Error**\n" + message)
