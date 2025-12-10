import asyncio
import json
import os
import logging
import numpy as np
import pandas as pd
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.config import settings
from core.data_feed import init_mt5
from core.mt5_trader import execute_order
from core.discord_notifier import notify_trade

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")


def compute_sl_tp_by_ai(
    entry_price: float,
    side: str,
    atr: float,
    regime: str,
    confidence: float,
) -> tuple[float, float]:
    """
    ฟังก์ชันเดียวกับใน main.py (copy logic มา)
    """
    atr = max(float(atr), 0.01)

    atr_mult_sl = 1.5
    rr = 1.8

    if regime == "trending" and confidence > 0.7:
        atr_mult_sl = 1.8
        rr = 2.3
    elif regime == "sideways":
        atr_mult_sl = 1.2
        rr = 1.4

    if confidence < 0.4:
        rr = max(1.0, rr - 0.4)

    sl_dist = atr * atr_mult_sl
    tp_dist = sl_dist * rr

    side = side.upper()
    if side == "BUY":
        sl_price = entry_price - sl_dist
        tp_price = entry_price + tp_dist
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - tp_dist

    sl_price = max(sl_price, 0.01)
    tp_price = max(tp_price, 0.01)
    return sl_price, tp_price


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

    state = load_last_state()

    # ถ้าเป็น AUTO ให้ดูจาก AI state ล่าสุด
    if side == "AUTO":
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
    volume = settings.MANUAL_TRADE_VOLUME

    # ใช้ข้อมูล AI ล่าสุดช่วยคิด SL/TP ถ้ามีพอ
    price = state.get("price")
    atr = state.get("atr")
    regime = state.get("regime", "unknown")
    confidence = state.get("ai_confidence", 0.0)

    sl_price = None
    tp_price = None
    if price is not None and atr is not None:
        sl_price, tp_price = compute_sl_tp_by_ai(
            entry_price=price,
            side=side,
            atr=atr,
            regime=regime,
            confidence=confidence,
        )

    # ยิงออเดอร์จริง
    result = await asyncio.to_thread(
        execute_order,
        settings.SYMBOL,
        side,
        volume,
        sl_price,
        tp_price,
    )

    # ✅ แจ้งเตือน Discord เฉพาะตอนออกออเดอร์ (manual / AUTO)
    try:
        msg = (
            f"DASHBOARD ORDER {side} {settings.SYMBOL} "
            f"{volume} lot SL={sl_price} TP={tp_price} (result={result})"
        )
        notify_trade(msg)
    except Exception:
        # กัน error จาก Discord ให้ไม่ทำให้ API 500
        pass

    return {
        "ok": True,
        "side": side,
        "volume": volume,
        "sl": sl_price,
        "tp": tp_price,
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

# ---------- API ประเมินความฉลาดของ AI จากไฟล์ log ----------


def _load_latest_ai_log() -> tuple[pd.DataFrame, str]:
    """
    โหลดไฟล์ ai_log_*.jsonl ล่าสุดจากโฟลเดอร์ logs
    """
    base_dir = os.path.dirname(settings.AI_LOG_PATH) or "logs"
    pattern = os.path.join(base_dir, "ai_log_*.jsonl")
    files = sorted([p for p in glob.glob(pattern)])
    if not files:
        raise FileNotFoundError("No ai_log_*.jsonl found")

    latest_path = files[-1]
    rows = []
    with open(latest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("latest log file is empty")

    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df.sort_values("time", inplace=True)

    # ให้แน่ใจว่ามีคอลัมน์ close
    if "close" not in df.columns and "Close" in df.columns:
        df["close"] = df["Close"]

    return df, latest_path


def _eval_ai_core(df: pd.DataFrame, horizon: int = 5, only_confirm: bool = False) -> Dict[str, Any]:
    df = df.copy()

    if only_confirm:
        df = df[df.get("confirm_signal", False)].copy()
        if df.empty:
            return {
                "samples": 0,
                "direction_acc": None,
                "winrate": None,
                "avg_pnl": None,
                "avg_win": None,
                "avg_loss": None,
            }

    df["future_close"] = df["close"].shift(-horizon)
    df = df.dropna(subset=["future_close"])

    if df.empty:
        return {
            "samples": 0,
            "direction_acc": None,
            "winrate": None,
            "avg_pnl": None,
            "avg_win": None,
            "avg_loss": None,
        }

    df["future_ret"] = df["future_close"] / df["close"] - 1.0

    df["pred_dir"] = np.where(df["ai_prob_up"] >= df["ai_prob_down"], 1, -1)
    df["true_dir"] = np.sign(df["future_ret"]).replace(0, 0)

    df["correct"] = df["pred_dir"] == df["true_dir"]
    df["pnl"] = np.where(df["pred_dir"] == 1, df["future_ret"], -df["future_ret"])

    total = int(len(df))
    direction_acc = float(df["correct"].mean()) if total else None
    winrate = float((df["pnl"] > 0).mean()) if total else None
    avg_pnl = float(df["pnl"].mean()) if total else None

    avg_win = df.loc[df["pnl"] > 0, "pnl"]
    avg_loss = df.loc[df["pnl"] < 0, "pnl"]

    avg_win_val = float(avg_win.mean()) if not avg_win.empty else None
    avg_loss_val = float(-avg_loss.mean()) if not avg_loss.empty else None

    return {
        "samples": total,
        "direction_acc": direction_acc,
        "winrate": winrate,
        "avg_pnl": avg_pnl,
        "avg_win": avg_win_val,
        "avg_loss": avg_loss_val,
    }

import glob  # อยู่ล่างสุดกันวง import ซ้อน
@app.get("/api/eval_ai")
async def api_eval_ai(horizon: int = 5):
    """
    ประเมินความฉลาดของ AI จากไฟล์ ai_log_*.jsonl ล่าสุด
    """
    try:
        df, latest_path = _load_latest_ai_log()
    except FileNotFoundError as e:
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=404,
        )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"load log error: {e}"},
            status_code=500,
        )

    try:
        metrics_all = _eval_ai_core(df, horizon=horizon, only_confirm=False)
        metrics_confirm = _eval_ai_core(df, horizon=horizon, only_confirm=True)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"eval error: {e}"},
            status_code=500,
        )

    return {
        "ok": True,
        "log_file": os.path.basename(latest_path),
        "horizon_bars": horizon,
        "all": metrics_all,
        "confirm": metrics_confirm,
    }