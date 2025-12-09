# core/position_sizing.py

from core.config import settings


def calculate_position_size(
    balance: float,
    atr: float,
    risk_percent: float | None = None,
) -> float:
    """
    คำนวณ volume (lot) จาก:
    - balance: ยอดเงินในบัญชี
    - atr: ค่า ATR ล่าสุด (เป็นราคาหน่วยเดียวกับ symbol)
    - risk_percent: เสี่ยงกี่ % ของ balance ต่อไม้

    สมมติ:
    risk_amount = balance * risk_percent
    SL distance = ATR_SL_MULTIPLIER * atr
    ค่าเสียหายต่อ 1 lot = (SL distance / TICK_SIZE) * TICK_VALUE
    volume = risk_amount / cost_per_lot
    """

    if risk_percent is None:
        risk_percent = settings.RISK_PER_TRADE

    if balance <= 0 or atr <= 0 or risk_percent <= 0:
        return settings.MIN_VOLUME

    risk_amount = balance * risk_percent

    sl_distance_price = settings.ATR_SL_MULTIPLIER * atr
    if sl_distance_price <= 0:
        return settings.MIN_VOLUME

    # price distance → points
    sl_points = sl_distance_price / settings.TICK_SIZE
    if sl_points <= 0:
        return settings.MIN_VOLUME

    cost_per_lot = sl_points * settings.TICK_VALUE
    if cost_per_lot <= 0:
        return settings.MIN_VOLUME

    volume = risk_amount / cost_per_lot

    # clamp volume ตาม min/max
    volume = max(settings.MIN_VOLUME, min(volume, settings.MAX_VOLUME))
    return round(volume, 2)  # ปัดเป็น 2 ตำแหน่ง เช่น 0.05, 0.10
