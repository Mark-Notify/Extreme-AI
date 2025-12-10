import asyncio
import json
import os
import logging
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.config import settings
from core.mt5_trader import execute_order
from core.data_feed import init_mt5
from core.discord_notifier import notify_trade  # 👈 เพิ่ม import ตรงนี้

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # return templates.TemplateResponse("classic_index.html", {"request": request})
    # return templates.TemplateResponse("minimal_index.html", {"request": request})
    # return templates.TemplateResponse("premium_index.html", {"request": request})
    return templates.TemplateResponse("luxury_index.html", {"request": request})


def load_last_state() -> Dict[str, Any]:
    path = settings.AI_LAST_STATE_PATH
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# @app.websocket("/ws")
# async def websocket_endpoint(ws: WebSocket):
#     await ws.accept()
#     try:
#         while True:
#             state = load_last_state()
#             await ws.send_json(state)
#             await asyncio.sleep(settings.DASHBOARD_REFRESH_SEC)  # หรือจะเปลี่ยนเป็น settings.DASHBOARD_REFRESH_SEC ก็ได้ ถ้าไปเพิ่มใน config แล้ว
#     except Exception:
#         await ws.close()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            state = load_last_state() or {}
            await ws.send_json(state)
            await asyncio.sleep(settings.DASHBOARD_REFRESH_SEC)
    except WebSocketDisconnect:
        # ฝั่ง client ปิดเอง (refresh แท็บ / ปิดหน้า) เคสปกติ ไม่ต้องถือว่าเป็น error
        # อยาก log ก็ตามสะดวก เช่น:
        # print("WebSocket disconnected")
        pass
    except asyncio.CancelledError:
        # task ถูก cancel ตอน server shutdown / reload
        # กลืน error ไปไม่ให้ traceback เด้ง
        # ถ้าอยากให้ FastAPI จัดการต่อ สามารถ `raise` ต่อได้ แต่ส่วนใหญ่ไม่จำเป็น
        # raise
        pass
    except Exception as e:
        # error จริง ๆ อย่างอื่นค่อย debug ทีหลัง
        # print(f"Unexpected WebSocket error: {e}")
        pass
    finally:
        # ปิด connection แบบ best-effort (เผื่อมันปิดไปแล้วก็ไม่ต้องสนใจ error)
        try:
            await ws.close()
        except Exception:
            pass



# ---------- API สำหรับปุ่ม BUY / SELL / AUTO / TRAIN ----------

class OrderRequest(BaseModel):
    side: str  # BUY / SELL / AUTO


@app.post("/api/order")
async def api_order(req: OrderRequest):
    side = req.side.upper()

    # AUTO = ให้ AI เลือกฝั่งจาก last_state
    if side == "AUTO":
        state = load_last_state()
        prob_up = state.get("ai_prob_up")
        prob_down = state.get("ai_prob_down")
        if prob_up is None or prob_down is None:
            return JSONResponse(
                {"ok": False, "error": "No AI state available for AUTO mode"},
                status_code=400,
            )
        side = "BUY" if prob_up >= prob_down else "SELL"

    if side not in ("BUY", "SELL"):
        return JSONResponse({"ok": False, "error": "Invalid side"}, status_code=400)

    # เตรียม MT5
    init_mt5()

    # lot เวลากดปุ่ม ใช้ค่าจาก config (.env → MANUAL_TRADE_VOLUME)
    volume = settings.MANUAL_TRADE_VOLUME

    # ยิงออเดอร์จริง (ทำใน thread แยก)
    result = await asyncio.to_thread(
        execute_order, settings.SYMBOL, side, volume
    )

    # ส่ง Discord เฉพาะตอนออกออเดอร์จาก Dashboard
    try:
        msg = (
            f"DASHBOARD ORDER {side} {settings.SYMBOL} "
            f"{volume} lot (result={result})"
        )
        notify_trade(msg)
    except Exception:
        # กัน error จาก Discord ไม่ให้ทำให้ API ล้ม
        pass

    return {
        "ok": True,
        "side": side,
        "volume": volume,
        "result": result,
    }


@app.post("/api/train_ai")
async def api_train_ai():
    """
    ปุ่ม Train AI → เรียก scripts.train_ai.main() ใน thread แยก
    """
    from scripts.train_ai import main as train_ai_main

    # รันเทรนใน thread แยก ไม่บล็อค request
    asyncio.create_task(asyncio.to_thread(train_ai_main))

    return {"ok": True, "message": "Training started"}
