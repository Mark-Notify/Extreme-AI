import json
from typing import Optional

import requests

from .config import settings


def _post(content: str, file_path: Optional[str] = None):
    if not settings.DISCORD_WEBHOOK_URL:
        return
    data = {"content": content}
    files = None
    if file_path:
        try:
            files = {"file": open(file_path, "rb")}
        except Exception as e:
            print("[DISCORD] file error:", e)

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


def notify_bot_started():
    _post("🚀 **Extreme AI v4 Bot Started**")


def notify_pre_signal(message: str, chart_path: Optional[str] = None):
    """
    เดิม: ส่ง Discord ตอน PRE
    ตอนนี้: ไม่ส่ง Discord แล้ว ตาม requirement
    ยัง log ลง console เผื่อ debug ได้
    """
    print("[DISCORD][SKIP PRE]", message)
    # ถ้าอยากปิดเงียบ ๆ เลย ก็ใช้ pass แทนได้:
    # pass


def notify_confirm_signal(message: str, chart_path: Optional[str] = None):
    """
    เดิม: ส่ง Discord ตอน CONFIRM
    ตอนนี้: ไม่ส่ง Discord แล้ว ตาม requirement
    ยัง log ลง console เผื่อ debug ได้
    """
    print("[DISCORD][SKIP CONFIRM]", message)
    # หรือจะเปลี่ยนเป็น pass เฉย ๆ ก็ได้
    # pass


def notify_trade(message: str):
    """
    ใช้เฉพาะ 'ตอนออกออเดอร์จริง' เท่านั้น
    - Auto trade จาก main.py
    - Manual trade จาก Dashboard (BUY / SELL / AUTO)
    """
    _post("🤖 **Executed Trade**\n" + message)


def notify_error(message: str):
    _post("⚠️ **Error**\n" + message)
